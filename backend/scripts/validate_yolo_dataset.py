"""Validate YOLO detection labels and check exact-image leakage between splits."""
import argparse
import hashlib
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Install PyYAML (included with Ultralytics): pip install -r requirements-ml.txt") from exc


def files_from_spec(root: Path, spec) -> list[Path]:
    paths: list[Path] = []
    entries = spec if isinstance(spec, list) else [spec]
    for entry in entries:
        path = Path(entry)
        path = path if path.is_absolute() else root / path
        if path.is_file() and path.suffix.lower() in {".txt", ".list"}:
            paths.extend((p if p.is_absolute() else root / p).resolve() for p in map(Path, path.read_text(encoding="utf-8").splitlines()) if p.name)
        elif path.is_dir():
            paths.extend(p.resolve() for p in path.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
        elif path.is_file():
            paths.append(path.resolve())
    return paths


def label_path(image: Path) -> Path:
    parts = list(image.parts)
    if "images" in parts:
        parts[parts.index("images")] = "labels"
        return Path(*parts).with_suffix(".txt")
    return image.with_suffix(".txt")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="YOLO dataset YAML")
    args = parser.parse_args()
    config_path = args.data.expanduser().resolve()
    if not config_path.is_file():
        parser.error(f"Dataset YAML does not exist: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    root = Path(config.get("path", config_path.parent))
    if not root.is_absolute():
        root = config_path.parent / root
    names = config.get("names", {})
    class_count = len(names)
    if not class_count:
        parser.error("Dataset YAML must define a non-empty names list or mapping.")
    splits = {key: files_from_spec(root, config[key]) for key in ("train", "val", "test") if config.get(key)}
    if "train" not in splits or "val" not in splits:
        parser.error("Dataset YAML must define train and val image paths.")
    if any(not images for images in splits.values()):
        parser.error("At least one configured split contains no supported image files.")
    problems: list[str] = []
    hashes: dict[str, set[str]] = {}
    image_count = 0
    label_count = 0
    for split, images in splits.items():
        for image in images:
            image_count += 1
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            seen_splits = hashes.setdefault(digest, set())
            if seen_splits and split not in seen_splits:
                problems.append(f"Exact image leakage across {', '.join(sorted(seen_splits))} and {split}: {image}")
            seen_splits.add(split)
            label = label_path(image)
            if not label.is_file():
                problems.append(f"Missing label file (use an empty file for background images): {label}")
                continue
            for line_number, line in enumerate(label.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                label_count += 1
                fields = line.split()
                try:
                    cls = int(fields[0])
                    coords = [float(value) for value in fields[1:]]
                    if len(coords) != 4 or not all(0 <= value <= 1 for value in coords):
                        raise ValueError("expected four normalized coordinates in [0, 1]")
                    if coords[2] <= 0 or coords[3] <= 0:
                        raise ValueError("box width and height must be positive")
                    if not 0 <= cls < class_count:
                        raise ValueError(f"class id {cls} is outside 0..{class_count - 1}")
                except (ValueError, IndexError) as exc:
                    problems.append(f"{label}:{line_number}: {exc}")
    print(f"Checked {image_count} images and {label_count} boxes across {', '.join(splits)}.")
    if problems:
        print(f"Found {len(problems)} dataset issue(s):")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("YOLO labels are structurally valid; no exact-image split leakage detected.")


if __name__ == "__main__":
    main()
