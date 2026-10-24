"""Evaluate a trained YOLO checkpoint on a held-out YOLO dataset split."""
import argparse
import json
from pathlib import Path
from time import perf_counter

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--weights", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default=None)
    p.add_argument("--split", choices=("val", "test"), default="test", help="Use test for final held-out evaluation")
    p.add_argument("--output", type=Path, default=None, help="Optional JSON metrics report path")
    args = p.parse_args()
    if not Path(args.weights).is_file():
        p.error(f"Weights not found: {args.weights}")
    if not Path(args.data).is_file():
        p.error(f"Dataset YAML not found: {args.data}")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install optional ML dependencies: pip install -r requirements-ml.txt") from exc
    model = YOLO(args.weights)
    kwargs = {"data": args.data, "imgsz": args.imgsz, "plots": True, "verbose": True, "split": args.split}
    if args.device is not None:
        kwargs["device"] = args.device
    started = perf_counter()
    metrics = model.val(**kwargs)
    elapsed = perf_counter() - started
    box = metrics.box
    names = getattr(model, "names", {})
    per_class = []
    indices = list(getattr(box, "ap_class_index", []))
    for position, class_id in enumerate(indices):
        precision = float(box.p[position])
        recall = float(box.r[position])
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class.append({
            "class_id": int(class_id), "class_name": names[int(class_id)] if isinstance(names, list) else names.get(int(class_id), str(class_id)),
            "precision": precision, "recall": recall, "f1": f1,
            "map50": float(box.ap50[position]), "map50_95": float(box.ap[position]),
        })
    report = {
        "weights": str(Path(args.weights).resolve()), "split": args.split,
        "results": {key: float(value) for key, value in metrics.results_dict.items() if isinstance(value, (int, float))},
        "per_class": per_class,
        "speed_ms_per_image": {key: float(value) for key, value in getattr(metrics, "speed", {}).items()},
        "evaluation_wall_seconds": round(elapsed, 3),
        "checkpoint_bytes": Path(args.weights).stat().st_size,
    }
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Saved evaluation report to {args.output.resolve()}")

if __name__ == "__main__":
    main()
