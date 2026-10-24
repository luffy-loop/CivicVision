# Model scripts

Install optional ML packages from `backend/requirements-ml.txt`. Prepare a YOLO-format dataset YAML with matching labels first. RDD2022 source annotations may require conversion; inspect the official dataset documentation and licensing before training.

From the `backend` directory:
```bash
python scripts/convert_voc_dataset.py --annotations /data/RDD2022/train/annotations --images /data/RDD2022/train/images --output /data/civicvision-yolo --seed 42
python scripts/validate_yolo_dataset.py --data /absolute/path/to/data.yaml
python scripts/train_yolo.py --data /absolute/path/to/data.yaml --epochs 50 --imgsz 640
python scripts/evaluate_yolo.py --weights runs/civicvision/road-damage/weights/best.pt --data /absolute/path/to/data.yaml --split test --output runs/civicvision/road-damage/test-metrics.json
```

The VOC converter emits YOLO images, labels, YAML and a class-count CSV. It groups exact and near-identical image hashes before a deterministic split. Review split composition; image hashing alone cannot establish capture-sequence or geographic independence. The validator checks label bounds/class IDs, missing annotation files and byte-identical images across splits. Run final evaluation on a held-out `test` split.

Set `MODEL_PATH` in `.env` to the trained checkpoint. Training output paths depend on your arguments and Ultralytics version; verify the checkpoint path before configuring the API.
