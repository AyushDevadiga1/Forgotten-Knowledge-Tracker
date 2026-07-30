# Sequence Diagrams

## 1. Tracking Loop Data Ingestion Sequence
```mermaid
sequenceDiagram
    participant OS as OS Sensors
    participant Tracker as track_loop
    participant CV as OCR/Webcam Pipeline
    participant Audio as Audio Pipeline
    participant DB as fkt_tracking.db

    loop Every 5 seconds
        Tracker->>OS: Poll interaction counters
        OS-->>Tracker: Returns key/mouse events
        
        Tracker->>CV: Fetch screen text & gaze estimation
        CV-->>Tracker: Returns [keywords] & attention score
        
        Tracker->>Audio: Poll microphone buffer
        Audio-->>Tracker: Calculate RMS, returns audio state
        
        Tracker->>Tracker: Evaluate intent heuristics 
        
        Tracker->>DB: Log session telemetry & concepts
    end
```

## 2. Review Session (SM-2 Update)
```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask Route
    participant LearningTracker
    participant DB as fkt_tracking.db

    User->>Browser: Selects Review Quality (1-5)
    Browser->>Flask Route: POST /api/v1/learning/reviews (quality=4)
    Flask Route->>LearningTracker: record_review("123", 4)
    
    LearningTracker->>DB: Query LearningItem WHERE id="123"
    DB-->>LearningTracker: (current item state)
    
    LearningTracker->>LearningTracker: Calculate new SM-2 interval
    
    LearningTracker->>DB: db.commit() -> UPDATE learning_items
    DB-->>LearningTracker: OK
    
    Flask Route-->>Browser: Redirect -> Next Due Item
```
