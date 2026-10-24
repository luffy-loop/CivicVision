import importlib.util
import sys
from pathlib import Path

from PIL import Image


def load_script(name: str):
    script = Path(__file__).parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_voc_converter_creates_repeatable_grouped_yolo_splits(tmp_path, monkeypatch):
    source_images = tmp_path / "source" / "images"
    annotations = tmp_path / "source" / "annotations"
    source_images.mkdir(parents=True)
    annotations.mkdir(parents=True)
    for index in range(12):
        image = Image.new("RGB", (64, 64))
        pixels = image.load()
        for y in range(64):
            for x in range(64):
                value = (x * (index + 3) * 17 + y * (index + 5) * 29 + x * y * (index + 1)) % 256
                pixels[x, y] = (value, (value * 3) % 256, (value * 7) % 256)
        image.save(source_images / f"road-{index}.jpg")
        (annotations / f"road-{index}.xml").write_text(
            f"<annotation><filename>road-{index}.jpg</filename><size><width>64</width><height>64</height></size>"
            "<object><name>pothole</name><bndbox><xmin>8</xmin><ymin>9</ymin><xmax>40</xmax><ymax>45</ymax></bndbox></object></annotation>",
            encoding="utf-8",
        )
    (source_images / "road-12.jpg").write_bytes((source_images / "road-0.jpg").read_bytes())
    (annotations / "road-12.xml").write_text(
        "<annotation><filename>road-12.jpg</filename><size><width>64</width><height>64</height></size>"
        "<object><name>pothole</name><bndbox><xmin>8</xmin><ymin>9</ymin><xmax>40</xmax><ymax>45</ymax></bndbox></object></annotation>",
        encoding="utf-8",
    )

    converter = load_script("convert_voc_dataset")
    outputs = [tmp_path / "converted-a", tmp_path / "converted-b"]
    assignments = []
    for output in outputs:
        monkeypatch.setattr(sys, "argv", ["convert_voc_dataset", "--annotations", str(annotations), "--images", str(source_images), "--output", str(output), "--seed", "17", "--val-fraction", "0.2", "--test-fraction", "0.2"])
        converter.main()
        split_for = {}
        for split in ("train", "val", "test"):
            files = list((output / "images" / split).glob("*.jpg"))
            assert files
            for image in files:
                split_for[image.stem] = split
        assert split_for["road-0"] == split_for["road-12"]
        assert (output / "data.yaml").is_file()
        assert (output / "dataset_summary.csv").is_file()
        assignments.append(split_for)
    assert assignments[0] == assignments[1]
