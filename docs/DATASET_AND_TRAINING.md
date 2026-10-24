# Dataset and training

## Dataset acquisition and terms

RDD2022 is linked from the [maintainer's RoadDamageDetector repository](https://github.com/sekilab/RoadDamageDetector) and its [Figshare dataset record](https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547). The maintainer describes JPEG images and Pascal VOC XML annotations for the labeled training data; the challenge test images are unannotated. Cite the dataset article ([DOI 10.1002/gdj3.260](https://doi.org/10.1002/gdj3.260)). Review and record the license and any reuse restrictions shown by Figshare before downloading, training, or distributing derived weights. License metadata could not be verified from this environment, so this project does not claim a license grant.

Do not commit the downloaded dataset. Keep labeled examples from its training portion separated into local train, validation and test groups; do not treat the unannotated challenge test images as a metric-bearing evaluation set. Group similar images before splitting to reduce adjacent-frame leakage.

## VOC conversion and validation

With Pillow installed, convert Pascal VOC XML and the matching images into a fresh output directory:

```powershell
cd backend
python scripts/convert_voc_dataset.py --annotations D:\datasets\RDD2022\train\annotations --images D:\datasets\RDD2022\train\images --output D:\datasets\civicvision-yolo --seed 42 --val-fraction 0.1 --test-fraction 0.1
python scripts/validate_yolo_dataset.py --data D:\datasets\civicvision-yolo\data.yaml
```

macOS/Linux: use the same arguments with absolute paths such as `/data/RDD2022/train/annotations`. Conversion sorts the discovered VOC class labels for stable IDs, clips valid VOC boxes to image edges, groups exact duplicates and images with 64-bit difference-hash distance within the configured threshold, then assigns whole groups deterministically. It copies image files and writes normalized YOLO labels, `data.yaml`, and `dataset_summary.csv`. Review the resulting split sizes and class distribution; perceptual similarity grouping is a leakage reduction aid, not proof that every geographic or sequence relationship has been separated.

The validator checks images/labels, class IDs, normalized boxes, and exact-byte image overlap across the YAML-defined splits. It does not validate license, sequence grouping, label semantics, or near-duplicate leakage independently.

## Train and evaluate

Install ML dependencies from `backend/requirements-ml.txt`. Pretrained weights may be downloaded by Ultralytics when you run training; choose a compatible model and comply with its own license. No weights are bundled here.

```powershell
cd backend
python scripts/train_yolo.py --data D:\datasets\civicvision-yolo\data.yaml --model yolo26n.pt --epochs 50 --imgsz 640 --batch 8 --device 0 --seed 42
python scripts/evaluate_yolo.py --weights runs\civicvision\road-damage\weights\best.pt --data D:\datasets\civicvision-yolo\data.yaml --split test --output runs\civicvision\road-damage\test-metrics.json
```

Use `--device cpu` for small CPU development runs, understanding that training can be slow. Ultralytics writes confusion matrix and PR plots as part of validation. Evaluation reports aggregate metrics, class-wise precision, recall, F1, mAP50, mAP50-95, inference timing reported by the validator, and checkpoint size. Manually review false positives and false negatives; no representative failure gallery has been produced for this repository. No training or evaluation has been run, so there are no accuracy results to report.

Set `MODEL_PATH` to the selected checkpoint and set `MODEL_VERSION` to a meaningful experiment identifier. Record the checkpoint hash, license, dataset provenance, split manifest and test report in the model card before release.
