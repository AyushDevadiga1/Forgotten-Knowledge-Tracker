# System Screenshots & Visual Outputs

This directory contains descriptive visual assets demonstrating the Forgotten Knowledge Tracker (FKT) interface, tracking loop, knowledge graph, and user feedback mechanisms.

## Visual Catalog

### CLI & System Operation
- **`cli_tracker_startup.png`**: Startup prompt for webcam permission and background model warm-up thread initialization (`main.py`).
- **`cli_tracking_loop_1.png`**: Multimodal background tracking loop executing screen OCR and window title extraction.
- **`cli_tracking_loop_2.png`**: Real-time intent classification and gaze attention score computation.
- **`system_flowchart.png`**: Architectural data flow diagram illustrating multimodal sensors -> Repository layer -> SM-2/AWFC memory model -> React Dashboard.

### Web Dashboard & UI Components
- **`dashboard_overview.png`**: Main system monitor dashboard displaying total concepts, active reviews, daily streak, and mini memory decay trends.
- **`dashboard_review_session.png`**: Interactive SM-2 review session interface for flashcard recall grading (quality 0–5).
- **`dashboard_knowledge_base.png`**: Filterable list of all tracked concepts with memory strength indicators and interval details.
- **`dashboard_graph_view.png`**: Visual Knowledge Graph displaying concept node clusters and knowledge gap callouts.
- **`dashboard_quiz_interrupt.png`**: Micro-Quiz interface displaying 4-option multiple-choice questions triggered by concept decay.
- **`dashboard_intent_toast.png`**: Non-intrusive floating `IntentFeedbackToast` for user correction of activity predictions.
- **`dashboard_add_concept.png`**: Form for manual concept addition with tag assignment and difficulty rating.
- **`dashboard_analytics.png`**: Analytical charts rendering tracking session timelines and intent classification confidence.
- **`dashboard_decay_chart.png`**: Attention-Weighted Forgetting Curve (AWFC) memory retention curves over 30-day intervals.
- **`dashboard_concept_history.png`**: Detailed concept timeline showing OCR encounters and attention scores at encoding.
- **`project_file_structure.png`**: Overview of FKT project file organization.
