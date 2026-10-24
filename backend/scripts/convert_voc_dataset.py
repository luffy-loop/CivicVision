"""Convert Pascal VOC image/XML annotations to YOLO with deterministic group splits."""
import argparse
import csv
import hashlib
import random
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageOps


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def difference_hash(image_path: Path) -> int:
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("L").resize((9, 8))
        pixels = image.load()
    value = 0
    for row in range(8):
        for column in range(8):
            value = (value << 1) | int(pixels[column, row] > pixels[column + 1, row])
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True, help="Directory of Pascal VOC XML annotations")
    parser.add_argument("--images", type=Path, required=True, help="Directory containing corresponding images")
    parser.add_argument("--output", type=Path, required=True, help="New output directory; must not already exist")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--test-fraction", type=float, default=0.1)
    parser.add_argument("--phash-distance", type=int, default=6, help="Join images whose 64-bit difference hashes are this close")
    args = parser.parse_args()
    annotations = args.annotations.expanduser().resolve()
    image_root = args.images.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not annotations.is_dir() or not image_root.is_dir():
        parser.error("Both --annotations and --images must name existing directories.")
    if output.exists():
        parser.error(f"Output directory already exists; choose a new path: {output}")
    if args.val_fraction <= 0 or args.test_fraction <= 0 or args.val_fraction + args.test_fraction >= 1:
        parser.error("Validation and test fractions must both be positive and sum to less than 1.")
    if not 0 <= args.phash_distance <= 8:
        parser.error("--phash-distance must be between 0 and 8.")

    image_index: dict[str, Path] = {}
    for path in image_root.rglob("*"):
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            if path.name in image_index:
                parser.error(f"Image basename is ambiguous: {path.name}")
            image_index[path.name] = path

    records = []
    class_names: set[str] = set()
    for xml_path in sorted(annotations.rglob("*.xml")):
        root = ET.parse(xml_path).getroot()
        filename = root.findtext("filename") or f"{xml_path.stem}.jpg"
        image_path = image_index.get(Path(filename).name)
        if image_path is None:
            parser.error(f"No image found for annotation {xml_path} (filename {filename})")
        with Image.open(image_path) as image:
            width, height = ImageOps.exif_transpose(image).size
        objects = []
        for obj in root.findall("object"):
            label = (obj.findtext("name") or "").strip()
            bounds = obj.find("bndbox")
            if not label or bounds is None:
                parser.error(f"Missing class or bndbox in {xml_path}")
            try:
                xmin, ymin, xmax, ymax = (float(bounds.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))
            except (TypeError, ValueError):
                parser.error(f"Invalid VOC bounding box in {xml_path}")
            xmin, xmax = max(0.0, xmin), min(float(width), xmax)
            ymin, ymax = max(0.0, ymin), min(float(height), ymax)
            if xmax <= xmin or ymax <= ymin:
                parser.error(f"Degenerate or out-of-image VOC box in {xml_path}")
            objects.append((label, xmin, ymin, xmax, ymax))
            class_names.add(label)
        records.append({"xml": xml_path, "image": image_path, "relative_image": image_path.relative_to(image_root), "width": width, "height": height, "objects": objects})
    if not records or not class_names:
        parser.error("No annotated images or classes were found.")

    # Exact bytes and close perceptual hashes are grouped so related frames remain in one split.
    union = UnionFind(len(records))
    exact_hashes: dict[str, int] = {}
    bands: dict[tuple[int, int], list[int]] = defaultdict(list)
    image_hashes = []
    for index, record in enumerate(records):
        raw_hash = hashlib.sha256(record["image"].read_bytes()).hexdigest()
        if raw_hash in exact_hashes:
            union.union(index, exact_hashes[raw_hash])
        else:
            exact_hashes[raw_hash] = index
        perceptual = difference_hash(record["image"])
        image_hashes.append(perceptual)
        for band in range(8):
            key = (band, (perceptual >> (band * 8)) & 0xFF)
            for previous in bands[key]:
                if (perceptual ^ image_hashes[previous]).bit_count() <= args.phash_distance:
                    union.union(index, previous)
            bands[key].append(index)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        groups[union.find(index)].append(index)
    group_items = list(groups.values())
    random.Random(args.seed).shuffle(group_items)
    total = len(records)
    targets = {"train": total * (1 - args.val_fraction - args.test_fraction), "val": total * args.val_fraction}
    assignments: dict[str, list[int]] = {"train": [], "val": [], "test": []}
    for group in group_items:
        if len(assignments["train"]) < targets["train"]:
            split = "train"
        elif len(assignments["val"]) < targets["val"]:
            split = "val"
        else:
            split = "test"
        assignments[split].extend(group)

    names = sorted(class_names)
    class_to_id = {name: index for index, name in enumerate(names)}
    for split, indices in assignments.items():
        for index in indices:
            record = records[index]
            image_dir = output / "images" / split
            label_dir = output / "labels" / split
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            relative_image = record["relative_image"].with_suffix(record["image"].suffix.lower())
            target_image = image_dir / relative_image
            target_image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record["image"], target_image)
            lines = []
            for label, xmin, ymin, xmax, ymax in record["objects"]:
                center_x = ((xmin + xmax) / 2) / record["width"]
                center_y = ((ymin + ymax) / 2) / record["height"]
                box_width = (xmax - xmin) / record["width"]
                box_height = (ymax - ymin) / record["height"]
                lines.append(f"{class_to_id[label]} {center_x:.8f} {center_y:.8f} {box_width:.8f} {box_height:.8f}")
            label_path = (label_dir / relative_image).with_suffix(".txt")
            label_path.parent.mkdir(parents=True, exist_ok=True)
            label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    yaml_lines = [f"path: {output.as_posix()}", "train: images/train", "val: images/val", "test: images/test", "names:"]
    yaml_lines.extend(f"  {index}: {name!r}" for name, index in class_to_id.items())
    (output / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    with (output / "dataset_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["split", "images", "boxes", "class", "class_boxes"])
        for split, indices in assignments.items():
            counts = Counter(obj[0] for index in indices for obj in records[index]["objects"])
            for class_name in names:
                writer.writerow([split, len(indices), sum(counts.values()), class_name, counts[class_name]])
    print(f"Converted {total} images into {len(groups)} perceptual groups at {output}")
    print("Split counts: " + ", ".join(f"{split}={len(items)}" for split, items in assignments.items()))
    print("Review the generated split distribution and ensure grouping reflects the source capture sequences before training.")


if __name__ == "__main__":
    main()
