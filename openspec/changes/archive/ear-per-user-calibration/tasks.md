## 1. Config

- [x] 1.1 Add CALIBRATION_DURATION_SECONDS (default 30) and CALIBRATION_MIN_SAMPLES (default 20) to config.py

## 2. Core Calibration

- [x] 2.1 Add calibrate_ear(duration_seconds) function to webcam_module.py that captures frames, computes EAR samples, and returns calibration data dict
- [x] 2.2 Modify compute_attention_score() to accept optional ear_low/ear_high parameters; fall back to 0.2/0.35 when not provided
- [x] 2.3 Extend session_state.py _DEFAULT schema with ear_calibration field (None by default)
- [x] 2.4 Add set_calibration(data) and get_calibration() functions to session_state.py
- [x] 2.5 Clear ear_calibration in stop() function

## 3. Loop Integration

- [x] 3.1 Insert calibration step in track_loop() at session-active transition (before first tracking cycle)
- [x] 3.2 Pass calibration data to compute_attention_score() in _get_attention_score() blend function

## 4. API

- [x] 4.1 Add POST /api/v1/session/calibrate endpoint that triggers calibration and returns result
- [x] 4.2 Extend GET /api/v1/session/status response to include ear_calibration field

## 5. Frontend

- [x] 5.1 Add calibrateSession() function to api.ts
- [x] 5.2 Add calibration progress indicator to SessionToggleButton.tsx (shown after Start Studying when webcam enabled)

## 6. Tests

- [x] 6.1 Add test: calibrate_ear returns valid calibration dict with mock webcam
- [x] 6.2 Add test: compute_attention_score uses calibration thresholds when provided
- [x] 6.3 Add test: compute_attention_score falls back to defaults when no calibration
- [x] 6.4 Add test: session_state set_calibration/get_calibration round-trips correctly
- [x] 6.5 Add test: stop() clears ear_calibration
- [x] 6.6 Verify all existing webcam and session_state tests still pass

## 7. Verification

- [x] 7.1 Run full test suite and confirm all pass
