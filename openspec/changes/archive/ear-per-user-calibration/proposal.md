## Why

EAR (Eye Aspect Ratio) thresholds in webcam_module.py are hardcoded to generic values (0.2 floor, 0.35 ceiling). These values vary significantly between users due to glasses, eye shape, lighting, and facial geometry. When thresholds are wrong for a given user, attention_at_encoding is systematically biased, corrupting AWFC memory decay for every concept learned in that session. A 30-second calibration at session start measures the user's personal EAR baseline and maps it to correct attention scores.

## What Changes

- Add calibrate_ear() function to webcam_module.py that captures frames over a configurable duration and computes per-user EAR baselines (open-eye mean, standard deviation)
- Extend compute_attention_score() to accept calibration parameters instead of hardcoded 0.2/0.35 thresholds
- Store calibration data in session_state.json (ear_calibration field)
- Add POST /api/v1/session/calibrate endpoint
- Insert calibration step in track_loop() at session-active transition
- Add frontend calibration modal with progress bar after Start Studying

## Capabilities

### New Capabilities

- ear-calibration: Per-user EAR baseline measurement and personalized attention scoring

### Modified Capabilities

(none -- no existing specs)

## Impact

- **Files modified**: tracker_app/tracking/webcam_module.py, tracker_app/tracking/session_state.py, tracker_app/tracking/loop.py, tracker_app/web/api.py, tracker_app/config.py, tracker_app/web/frontend/src/api.ts, tracker_app/web/frontend/src/components/SessionToggleButton.tsx
- **New files**: tracker_app/tests/test_ear_calibration.py
- **Schema change**: session_state.json gains ear_calibration field
- **No API breaking changes**: Existing /session/start and /session/stop remain identical
- **Backward compatible**: If no calibration data exists, falls back to current hardcoded thresholds
