## Purpose

Ensures that study content captured by OCR and browser ingest is persisted and actually used: deck answers and quiz questions derive from real captured text, graph edges reflect real co-occurrence, telemetry rows are written by the runtime, and seed/demo data can never be mistaken for real captures.

## ADDED Requirements

### Requirement: Persist real capture content as encounter context
The system SHALL store a sanitized excerpt of the actual captured text as the encounter context for the concepts it extracts. OCR captures SHALL persist a text excerpt (not the literal token `ocr`), and browser ingest SHALL persist a sanitized excerpt of the selected text (not only the window title), whenever the text passes the existing privacy and quality gates. Sensitive windows and redacted text SHALL persist nothing.

#### Scenario: OCR capture persists a text excerpt
- **WHEN** an OCR capture returns extracted keywords and non-empty text that passes quality checks, and those keywords become concept encounters
- **THEN** the newest encounter for each concept has a context snippet containing a sanitized excerpt of that text, and the recorded context is never the literal `ocr`

#### Scenario: Browser ingest persists the selected text
- **WHEN** `/api/v1/ingest` receives a title and selected study text that passes privacy and quality filters
- **THEN** the extracted concepts persist a context snippet containing a sanitized excerpt of the selected text, not just `browser:<title>`

#### Scenario: Sensitive or noisy text persists nothing
- **WHEN** OCR or ingest text is redacted, sensitive, or fails the quality gate
- **THEN** no excerpt is persisted for those concepts

### Requirement: Deck answers are derived from real content
Auto-promotion of a concept into the learning deck SHALL require a real content excerpt to exist; the deck answer SHALL be built from that excerpt. Concepts without any real excerpt SHALL NOT auto-promote and SHALL NOT produce placeholder answers in the deck.

#### Scenario: Promotion with real content
- **WHEN** a concept has persisted capture content and reaches the promotion threshold
- **THEN** the resulting deck item's answer references that content, and no template placeholder text is used

#### Scenario: Promotion blocked without content
- **WHEN** a concept is re-encountered the required number of times but has no real persisted excerpt
- **THEN** the concept does not become a deck item, and no placeholder-answer deck item is created on its behalf

### Requirement: Micro-quiz questions are content-backed
The micro-quiz SHALL only test concepts that have persisted capture content, and SHALL NOT emit a bare self-report question ("Which of these concepts have you been studying?") about a keyword with no content.

#### Scenario: Quiz built from content-backed concepts
- **WHEN** at least one concept with persisted content exists and a quiz is due
- **THEN** the quiz question references the concept's captured material and omits concepts lacking content

#### Scenario: No meaningful quiz available
- **WHEN** no concept has persisted content
- **THEN** no micro-quiz is emitted for that cycle

### Requirement: Graph edges reflect co-occurrence within capture windows
The knowledge graph SHALL create an edge between two concepts when they are captured together in the same capture window, so the graph represents concepts the user actually studied concurrently. Concepts never captured together SHALL remain disconnected.

#### Scenario: Co-captured concepts gain an edge
- **WHEN** two concepts are extracted from the same capture window
- **THEN** the graph has an edge between them

#### Scenario: Unrelated concepts stay disconnected
- **WHEN** two concepts are never extracted from the same capture window
- **THEN** the graph has no edge between them

### Requirement: Telemetry is written by the runtime tracker
The tracking loop SHALL persist a multi-modal log row for each capture cycle it runs (timestamp, window title, keywords, audio label, attention score, intent), and the telemetry summary SHALL count those rows exactly as it counts existing logs. Metrics SHALL be persisted from real sessions, not only from seed tools.

#### Scenario: A capture cycle writes a telemetry row
- **WHEN** the tracking loop completes a capture cycle
- **THEN** a new multi-modal log row with that cycle's data is persisted

#### Scenario: Telemetry summary includes runtime rows
- **WHEN** the telemetry summary is requested within 24 hours of a tracking-loop capture
- **THEN** `total_logs` is at least the number of rows written by the runtime loop in that window

### Requirement: Seed data cannot be mistaken for real data
The seed tool SHALL refuse to run unless explicitly enabled, and SHALL mark the rows it writes as seed so dashboards and audits can distinguish demo data from real captures.

#### Scenario: Seed without explicit enablement refuses
- **WHEN** the seed tool is invoked without the enabling flag or environment variable
- **THEN** it aborts and writes no data to the real database

#### Scenario: Seeded rows are identifiable
- **WHEN** the seed tool runs with explicit enablement
- **THEN** it writes only into the designated target and the seeded rows are clearly marked as seed

### Requirement: Deck excludes fragment and duplicate concepts
Deck promotion and backfill SHALL exclude near-duplicate single-word fragments and duplicate captures so `learning_items` contains one question per distinct study concept.

#### Scenario: Duplicate captures are deduplicated
- **WHEN** the same concept is captured under differing but equivalent forms or multiple times
- **THEN** at most one deck item exists for it

#### Scenario: Fragment terms are excluded
- **WHEN** a single-word capture is already covered by a deck-eligible multi-word concept (e.g. "cellular" vs "cellular respiration")
- **THEN** the fragment is not promoted to the deck
