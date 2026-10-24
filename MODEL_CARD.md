# Model card — CivicVision

## Current state
No trained road-damage checkpoint is included. By default, the app is in demo mode and intentionally returns zero detections with an explanatory message. It does not fabricate road-damage predictions.

No training, validation, or held-out test run has been performed for this repository. There are no measured metrics or representative error examples to report. The API's configured model adapter loads the configured checkpoint once per process and reports a service error if it cannot load or run.

## Intended use
Assistance for reviewing user-submitted road images and organizing reports for human review.

## Out of scope
- Certifying road safety or structural integrity.
- Determining accident likelihood.
- Automatically submitting complaints to a public authority.
- Replacing professional engineering inspection.

## Evaluation required before release
- Test/train split and dataset provenance.
- Per-class precision, recall, F1, mAP@0.5 and mAP@0.5:0.95.
- Local image evaluation across weather, lighting, camera angles and road surfaces.
- Latency, memory and throughput on target hardware.
- False positive/negative review and confidence calibration.

## Known limitations
Performance may degrade on images unlike the training data. Confidence is not severity. Rule-based priority is only a triage aid. Reports require human verification.

## Evaluation status

Not evaluated. Do not interpret the training/evaluation scripts or this model card as evidence of model accuracy. Before deployment, record dataset/license provenance, split strategy, checkpoint hash, per-class precision/recall/F1, mAP@0.5 and mAP@0.5:0.95, and reviewed false-positive/false-negative examples here.
