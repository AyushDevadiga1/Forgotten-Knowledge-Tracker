## Purpose

Measure a per-user EAR baseline at session start and use it to normalize attention scores, replacing hardcoded thresholds that fail for users with different eye geometry, glasses, or lighting conditions.

## ADDED Requirements

### Requirement: EAR baseline calibration
The system SHALL capture EAR values over a configurable duration (default 30 seconds) at session start and compute per-user baselines: mean open-eye EAR and standard deviation.

#### Scenario: Successful calibration with webcam
- **WHEN** the user starts a session with webcam enabled
- **THEN** the system captures EAR samples for the calibration duration
- **AND** computes personal_ear_low (mean - 1.5 * std) and personal_ear_high (mean + 1.0 * std)
- **AND** stores the calibration data in session_state.json

#### Scenario: Calibration with no face detected
- **WHEN** calibration runs but no face is detected for >= 80% of samples
- **THEN** the system falls back to hardcoded default thresholds (0.2 / 0.35)
- **AND** stores calibration data with a fallback flag

#### Scenario: Calibration skipped (no webcam)
- **WHEN** the user starts a session without webcam enabled
- **THEN** no calibration runs and hardcoded thresholds are used

### Requirement: Personalized attention scoring
compute_attention_score() SHALL accept optional calibration parameters and use them instead of hardcoded thresholds when provided.

#### Scenario: Attention score with calibration
- **WHEN** calibration data exists for the current session
- **THEN** attention score is computed using personal_ear_low as floor and personal_ear_high as ceiling
- **AND** the output range remains 0-100

#### Scenario: Attention score without calibration
- **WHEN** no calibration data exists
- **THEN** attention score falls back to hardcoded 0.2/0.35 thresholds (current behavior)

### Requirement: Calibration data persistence
Calibration data SHALL be stored in session_state.json under an ear_calibration key and cleared when the session stops.

#### Scenario: Calibration survives tracker restart
- **WHEN** calibration is completed and the tracker process restarts
- **THEN** the calibration data is still available in session_state.json

#### Scenario: Calibration cleared on session stop
- **WHEN** the user stops the session
- **THEN** ear_calibration is cleared from session_state.json

### Requirement: API endpoint for calibration
The system SHALL expose POST /api/v1/session/calibrate that triggers calibration and returns the result.

#### Scenario: Trigger calibration via API
- **WHEN** POST /api/v1/session/calibrate is called with {duration_seconds: 30}
- **THEN** the system runs calibration and returns {calibrated: true, personal_ear_low, personal_ear_high, duration_seconds}

### Requirement: Frontend calibration UX
The frontend SHALL display a calibration progress indicator after the user clicks Start Studying when webcam is enabled.

#### Scenario: Calibration modal shown
- **WHEN** user clicks Start Studying with webcam enabled
- **THEN** a calibration progress indicator appears for the calibration duration
- **AND** concept capture does not begin until calibration completes
