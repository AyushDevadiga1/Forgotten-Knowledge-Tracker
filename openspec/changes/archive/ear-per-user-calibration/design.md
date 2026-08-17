## Context

webcam_module.py computes EAR from 6 MediaPipe face landmarks per eye. The current compute_attention_score() uses hardcoded thresholds (0.2 floor, 0.35 ceiling) that assume average eye geometry. The attention score feeds into AWFC memory decay, intent classification, and quiz gating. Calibration needs to happen once at session start before concept capture begins.

## Goals / Non-Goals

**Goals:**
- Measure per-user EAR baseline in 30 seconds at session start
- Map personal EAR range to 0-100 attention score using personal baselines
- Store calibration data in session_state.json for cross-process access
- Fall back gracefully to hardcoded thresholds when calibration fails

**Non-Goals:**
- Real-time adaptive calibration (continuous re-baseline during session)
- Per-eye calibration (currently both eyes are averaged)
- Lighting adaptation or face angle normalization
- Frontend display of live EAR values (internal signal only)

## Decisions

### Calibration algorithm
Capture ~30 EAR samples over 30 seconds (1 sample/sec). The user is instructed to look at the screen normally (eyes open). Compute:
- mean_ear = mean of all samples
- std_ear = standard deviation of samples
- personal_ear_low = mean_ear - 1.5 * std_ear (floor for closed/drowsy)
- personal_ear_high = mean_ear + 1.0 * std_ear (ceiling for wide open)

The asymmetric multipliers (1.5 low, 1.0 high) account for the fact that EAR drops sharply when eyes close but increases modestly when eyes are wide open.

**Alternatives considered:**
- Percentile-based (5th/95th): Less robust with only 30 samples
- User-initiated blink calibration: More accurate but UX friction
- Z-score normalization: Requires storing mean+std, more complex, same result

### Storage location
Store calibration in session_state.json under ear_calibration key. This is the existing cross-process IPC file with filelock protection. The schema becomes:

`json
{
  "active": true,
  "started_at": "...",
  "stopped_at": null,
  "ear_calibration": {
    "personal_ear_low": 0.15,
    "personal_ear_high": 0.30,
    "mean_ear": 0.23,
    "std_ear": 0.05,
    "calibrated_at": "...",
    "fallback": false
  }
}
`

### Calibration hook point
Insert calibration in track_loop() when session transitions from inactive to active (loop.py ~line 323). The webcam pipeline is already warm at this point. Calibration runs synchronously before the first tracking cycle, blocking concept capture until complete.

**Alternatives considered:**
- Separate POST /session/calibrate endpoint: More flexible but requires frontend orchestration
- Calibration inside session_state.start(): Runs in web process, webcam not available
- Frontend-triggered calibration: Adds complexity, same result

### Fallback strategy
If <20% of calibration samples have a detected face, or if the computed range is invalid (personal_ear_low < 0.05 or personal_ear_high > 0.5), fall back to hardcoded 0.2/0.35 thresholds and set fallback=true in the calibration data.

## Risks / Trade-offs

- **30-second delay at session start**: User must wait before studying begins. -> Mitigation: Show progress indicator; 30s is acceptable for a study session that lasts minutes to hours.
- **Calibration accuracy with glasses**: Glasses can cause MediaPipe to miss eye landmarks. -> Mitigation: Fallback to defaults; user can retry.
- **Lighting changes**: Calibration in one lighting condition may not transfer. -> Mitigation: The std_ear captures some variance; the range is wide enough to tolerate moderate lighting shifts.
- **session_state.json size**: Adds ~200 bytes. -> Mitigation: Negligible.
