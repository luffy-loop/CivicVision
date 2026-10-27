"""Train or resume a YOLO road-damage detector from a prepared dataset.

Examples:
  python scripts/train_yolo.py --data /path/to/data.yaml --model yolo11n.pt --epochs 50
  python scripts/train_yolo.py --data /path/to/data.yaml --resume-from runs/civicvision/road-damage/weights/last.pt

Validate the dataset before training and evaluate the selected checkpoint on the held-out test split.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Path to dataset YAML in YOLO format")
    parser.add_argument("--model", default="yolo11n.pt", help="Pretrained checkpoint or compatible weights file")
    parser.add_argument("--resume-from", type=Path, help="Resume an interrupted run from its last.pt checkpoint")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default=None, help="Optional device, e.g. 0 or cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--project", default="runs/civicvision")
    parser.add_argument("--name", default="road-damage")
    args = parser.parse_args()

    data = Path(args.data).expanduser().resolve()
    if not data.is_file():
        parser.error(f"Dataset YAML does not exist: {data}")
    if args.epochs < 1 or args.imgsz < 128 or args.batch < 1:
        parser.error("epochs and batch must be positive; imgsz must be at least 128")

    resume_from = args.resume_from.expanduser().resolve() if args.resume_from else None
    if resume_from and not resume_from.is_file():
        parser.error(f"Resume checkpoint does not exist: {resume_from}")
    if resume_from and args.model != "yolo11n.pt":
        parser.error("--model cannot be combined with --resume-from; the resume checkpoint supplies the model")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install optional ML dependencies: pip install -r requirements-ml.txt") from exc

    model = YOLO(str(resume_from) if resume_from else args.model)
    train_kwargs = {
        "data": str(data),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": str(Path(args.project).expanduser()),
        "name": args.name,
        "patience": 12,
        "plots": True,
        "save": True,
        "seed": args.seed,
        "deterministic": True,
        "resume": bool(resume_from),
    }
    if args.device is not None:
        train_kwargs["device"] = args.device

    result = model.train(**train_kwargs)
    save_dir = Path(getattr(result, "save_dir", Path(args.project).expanduser() / args.name)).expanduser()
    best = save_dir / "weights" / "best.pt"
    last = save_dir / "weights" / "last.pt"
    metadata = {
        "experiment": args.name,
        "started_from": str(resume_from) if resume_from else args.model,
        "resume": bool(resume_from),
        "dataset_yaml": str(data),
        "epochs_requested": args.epochs,
        "image_size": args.imgsz,
        "batch_size": args.batch,
        "device": args.device or "auto",
        "seed": args.seed,
        "deterministic": True,
        "best_checkpoint": str(best.resolve()),
        "best_checkpoint_exists": best.is_file(),
        "best_checkpoint_sha256": sha256_file(best),
        "last_checkpoint": str(last.resolve()),
        "last_checkpoint_exists": last.is_file(),
        "dataset_sha256": sha256_file(data),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_status": "not evaluated",
    }
    save_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = save_dir / "civicvision-model-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Training run directory: {save_dir.resolve()}")
    print(f"Best checkpoint: {best.resolve()} (exists={best.is_file()})")
    print(f"Last checkpoint: {last.resolve()} (exists={last.is_file()})")
    print(f"Experiment metadata: {metadata_path.resolve()}")
    if not best.is_file():
        raise SystemExit("Training ended without best.pt; inspect the Ultralytics training output before deployment.")
    print("Next: evaluate best.pt on the held-out test split before configuring MODEL_PATH.")


if __name__ == "__main__":
    main()
