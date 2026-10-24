"""Train a YOLO road-damage detector from a prepared YOLO-format dataset.

Example:
  python scripts/train_yolo.py --data path/to/data.yaml --epochs 50 --imgsz 640

You must prepare and validate dataset annotations before training.
"""
import argparse
import json
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to dataset YAML in YOLO format")
    parser.add_argument("--model", default="yolo26n.pt", help="Compatible pretrained YOLO checkpoint")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default=None, help="Optional device, e.g. 0, cpu")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used by the training runtime")
    parser.add_argument("--project", default="runs/civicvision")
    parser.add_argument("--name", default="road-damage")
    args = parser.parse_args()
    data = Path(args.data).expanduser().resolve()
    if not data.is_file():
        parser.error(f"Dataset YAML does not exist: {data}")
    if args.epochs < 1 or args.imgsz < 128 or args.batch < 1:
        parser.error("epochs and batch must be positive; imgsz must be at least 128")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install optional ML dependencies: pip install -r requirements-ml.txt") from exc
    model = YOLO(args.model)
    train_kwargs = dict(data=str(data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, project=args.project, name=args.name, patience=12, plots=True, save=True, seed=args.seed, deterministic=True)
    if args.device is not None:
        train_kwargs["device"] = args.device
    model.train(**train_kwargs)
    best = Path(args.project) / args.name / "weights" / "best.pt"
    print(f"Training finished. Expected best checkpoint: {best.resolve()}")
    run_dir = Path(args.project) / args.name
    metadata = {
        "experiment": args.name, "pretrained_checkpoint": args.model,
        "dataset_yaml": str(data), "epochs": args.epochs, "image_size": args.imgsz,
        "batch_size": args.batch, "device": args.device or "auto", "seed": args.seed,
        "deterministic": True, "checkpoint": str(best.resolve()),
        "checkpoint_exists": best.is_file(), "evaluation_status": "not evaluated",
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "civicvision-model-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved experiment metadata: {(run_dir / 'civicvision-model-metadata.json').resolve()}")
    print("Evaluate the checkpoint on a held-out test set before configuring MODEL_PATH.")

if __name__ == "__main__":
    main()
