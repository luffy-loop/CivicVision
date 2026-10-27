# Dataset and training

## Dataset acquisition and terms

RDD2022 is linked from the [maintainer's RoadDamageDetector repository](https://github.com/sekilab/RoadDamageDetector) and its [Figshare dataset record](https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547). The maintainer describes JPEG images and Pascal VOC XML annotations for the labeled training data; the challenge test images are unannotated. Cite the dataset article ([DOI 10.1002/gdj3.260](https://doi.org/10.1002/gdj3.260)). Review and record the license and any reuse restrictions shown by Figshare before downloading, training, or distributing derived weights. This project does not claim a license grant.

Do not commit the downloaded dataset or model weights. Keep labeled examples from the dataset's annotated training portion separated into local train, validation and test groups; do not treat the unannotated challenge test images as an evaluation set. Group similar images before splitting to reduce adjacent-frame leakage.

## VOC conversion and validation

Install the optional dependencies from `backend/requirements-ml.txt`. With Pillow installed, convert Pascal VOC XML and matching images into a fresh output directory:

```powershell
cd backend
python scripts/convert_voc_dataset.py --annotations D:\datasets\RDD2022\train\annotations --images D:\datasets\RDD2022\train\images --output D:\datasets\civicvision-yolo --seed 42 --val-fraction 0.1 --test-fraction 0.1
python scripts/validate_yolo_dataset.py --data D:\datasets\civicvision-yolo\data.yaml
```

Conversion sorts the discovered VOC class labels for stable IDs, clips valid VOC boxes to image edges, groups exact duplicates and images with 64-bit difference-hash distance within the configured threshold, then assigns whole groups deterministically. It copies image files and writes normalized YOLO labels, `data.yaml`, and `dataset_summary.csv`. Review split sizes and class distribution. Perceptual grouping helps reduce leakage but does not prove complete geographic or sequence separation.

The validator checks image/label presence, class IDs, normalized boxes, and exact-byte image overlap across the YAML-defined splits. It does not independently validate license, sequence grouping, label semantics, or perceptual duplicates across splits.

## Train and resume

Use a supported pretrained checkpoint. This repository has used `yolo11n.pt`; choose the model family available in your installed Ultralytics version. First validate the dataset, then train:

```powershell
cd backend
python scripts/validate_yolo_dataset.py --data D:\datasets\civicvision-yolo\data.yaml
python scripts/train_yolo.py --data D:\datasets\civicvision-yolo\data.yaml --model yolo11n.pt --epochs 50 --imgsz 640 --batch 8 --device 0 --seed 42 --project D:\civicvision-runs --name road-damage-v1
```

To resume an interrupted run, pass the `last.pt` checkpoint using `--resume-from`. Ultralytics resumes the saved run state; this differs from starting a new fine-tuning run from `best.pt`. The script writes `civicvision-model-metadata.json` beside the output, including checkpoint existence and SHA-256 hashes. Save the run directory to durable storage (for example, Google Drive when training in Colab), not just the temporary runtime filesystem.

Example resume:

```powershell
python scripts/train_yolo.py --data D:\datasets\civicvision-yolo\data.yaml --resume-from D:\civicvision-runs\road-damage-v1\weights\last.pt --epochs 50 --imgsz 640 --batch 8 --device 0 --seed 42 --project D:\civicvision-runs --name road-damage-v1
```

Use `--device cpu` for small CPU development runs, understanding that training can be slow. Choose a new run name for a new experiment to prevent mixing outputs. When continuing a completed run with new labels or tuning, start a new run from the chosen `best.pt` checkpoint instead of resuming a finished run.

## Held-out evaluation

```powershell
python scripts/evaluate_yolo.py --weights D:\civicvision-runs\road-damage-v1\weights\best.pt --data D:\datasets\civicvision-yolo\data.yaml --split test --imgsz 640 --device 0 --output D:\civicvision-runs\road-damage-v1\test-metrics.json
```

The report includes aggregate metrics, per-class precision, recall, F1, mAP50, mAP50-95, timing, and checkpoint size. Review false positives and false negatives manually; do not treat model confidence as road-defect severity or a safety assessment. Do not configure `MODEL_PATH` until test evaluation and a manual prediction review are complete.

Before distributing model weights, document checkpoint hash, license, dataset provenance, split summary, and test report. No accuracy result is claimed by this repository without a recorded evaluation report.
