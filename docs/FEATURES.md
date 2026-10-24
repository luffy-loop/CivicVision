# Feature scope

## Included in this starter
- Road image upload and validation
- API-based scan workflow
- Explicit demo mode with no fabricated detections
- Optional configured YOLO model adapter
- Report submission and persistent records
- Optional coordinates and an OpenStreetMap-backed interactive map with category/status filters
- Report status transitions, validation, evidence view and status history
- Search, category/status filtering and offset pagination
- CSV export and summary metrics
- Candidate duplicate suggestions by category, proximity and time window
- Image brightness/contrast warning
- Responsive dashboard, scanner with downloadable annotated image, reports, map and analytics
- Loading states, validation feedback, icons, transitions, reduced-motion support
- VOC-to-YOLO conversion, perceptual grouping, dataset validation, model metrics scripts, API tests, CI, Dockerfiles and setup docs

## Deliberately not represented as complete
- Citizen accounts and reviewer/admin roles (only a preview shared-key gate protects status updates)
- Production object storage and image retention workflows

- Notifications/email/SMS
- Municipal API integration
- A trained model checkpoint
- Telugu localization
- Date-range analytics and map filters
- Duplicate confirmation/dismissal and image similarity
- Previous/current report comparison and change timeline
- Reviewer corrections and versioned training-data export
- Automated severity measurement from physical dimensions
- A production migration framework
- Production observability and rate limiting

These need implementation/configuration before public production use.
