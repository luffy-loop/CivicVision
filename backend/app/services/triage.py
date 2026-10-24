def normalized_kind(label: str) -> str:
    value = label.strip().lower().replace("_", " ").replace("-", " ")
    # Common RDD-style codes: D00/D10/D20 are crack classes; D40 is pothole.
    if "pothole" in value or value == "d40" or value.startswith("d40 "):
        return "pothole"
    if "crack" in value or value in {"d00", "d10", "d20"} or value.startswith(("d00 ", "d10 ", "d20 ")):
        return "crack"
    return "other"

def estimate_priority(detections: list[dict]) -> str:
    """Transparent heuristic for triage only; not an engineering safety assessment."""
    if not detections:
        return "review"
    kinds = [normalized_kind(str(d.get("label", ""))) for d in detections]
    if "pothole" in kinds and len(detections) >= 2:
        return "high"
    if "pothole" in kinds:
        return "medium"
    if "crack" in kinds:
        return "low"
    return "review"

def explain_priority(detections: list[dict], detector_mode: str) -> str:
    if detector_mode != "model":
        return "Human review required: no configured model prediction was available."
    if not detections:
        return "No model detections above threshold; human review required."
    kinds = [normalized_kind(str(item.get("label", ""))) for item in detections]
    if "pothole" in kinds and len(detections) >= 2:
        return "Rule-based triage: multiple model detections include a pothole; verify manually."
    if "pothole" in kinds:
        return "Rule-based triage: one model detection is mapped to pothole; verify manually."
    if "crack" in kinds:
        return "Rule-based triage: model detections are mapped to road cracks; verify manually."
    return "Rule-based triage: detected classes do not match pothole or crack labels; verify manually."
