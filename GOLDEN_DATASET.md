# FKT Golden Dataset — Capture & Label Guide

A **golden dataset** is a small, hand-labeled set of real study screenshots used to measure how accurately FKT's pipeline (OCR → keyword extraction → intent) extracts concepts, preserves hierarchy, and judges intent. It is ground truth we control, so every future fix becomes a measured change instead of a guess.

## 1. Where things live

```
data/golden/
  001-my-slug.png        ← your screenshot (unique id + short slug)
  001-label.json         ← your manual labels for that screenshot
  002-...
```

Create the directory once:

```powershell
New-Item -ItemType Directory -Path data\golden
```

## 2. How many and what kind

Start with **30 screenshots** across `5` study modes, 5–7 each:

| Mode | Examples to capture |
|---|---|
| `textbook_pdf` | Physics/CS textbook page, lecture notes PDF |
| `code_ide` | VS Code / IDE with code or a README open |
| `lecture_video` | A lecture/explainer video playing, slides visible |
| `notes_app` | Notion/Obsidian/OneNote notes |
| `browser_article` | A long-form article or documentation site |

Mix in a few genuinely-non-study screenshots (chat app, video games) so the intent label test knows what "not studying" looks like.

## 3. Taking a screenshot (Windows)

1. Bring the study window you want captured to the **foreground** (FKT only looks at the active window).
2. Press **`Win` + `Shift` + `S`** (Snipping Tool) and drag-select the window (or just the content region).
3. Paste it into Paint, or it saves automatically with **`Win` + `Print Screen`**.
4. Save it into `data/golden/` with a **sequential id + slug**, e.g. `007-recursion-bst-notes.png`.

Rules:
- **Capture before** closing the window, the same way FKT would see it (also include the window title bar — FKT reads `window_title`).
- **Do not** include passwords, credit cards, private chats, or medical info. Golden data stays on your machine, same as FKT's privacy rule.
- **No duplicates** — each screenshot should show genuinely different content.

## 4. Labeling a screenshot

For each screenshot create `<id>-label.json` next to it:

```powershell
New-Item -ItemType File -Path data\golden\007-readme.md-notes-label.json
```

Copy this template and fill it in:

```json
{
  "id": "007",
  "source": "Obsidian notes, Node.js TPS module",
  "mode": "notes_app",
  "theme": "webdev/node-basics",
  "true_intent": "studying",
  "expected_concepts": [
    "module system",
    "require",
    "commonjs",
    "nodejs",
    "event loop"
  ],
  "expected_hierarchy": {
    "title": "Node.js basics",
    "sections": [
      { "heading": "Module system", "level": 1 }
    ]
  },
  "notes": "written while following a tutorial"
}
```

### What each field means

| Field | Meaning | Rule of thumb |
|---|---|---|
| `id` | Must match the file prefix | numeric, 3 digits |
| `source` | Where the screenshot came from | short phrase, helps you later |
| `mode` | One of the 5 study modes above | pick the closest |
| `theme` | The subject/topic | broad, e.g. `dsa/sorting` |
| `true_intent` | What you were actually doing: `studying`, `passive`, or `idle` | **Most important field** — this is the ground truth for the misclassification bug |
| `expected_concepts` | Terms a good extractor *should* find | 5–10 real concepts, in lowercase |
| `expected_hierarchy` | The document structure you can see | title + headings you can spot; omit if none |
| `focused_tab_title` | The browser tab that is frontmost when the frame was captured | e.g. `Two Sum - LeetCode` |
| `focused_tab_url` | The address of that tab | e.g. `https://leetcode.com/problems/two-sum/` |
| `notes` | Anything that matters for later review | optional |

- [ ] 30 screenshots, 5–7 per mode, varied real content
- [ ] Every screenshot has a matching `-label.json` with the same `id`
- [ ] `true_intent` is filled honestly (that's what fixes "studying detected as idle")
- [ ] `expected_concepts` are the *main* ideas, not every word
- [ ] No sensitive/private content captured

## 6. What happens next

The evaluation runner (`tools/golden_eval.py`) will be built to:

1. Run the real `ocr_pipeline()` on every `*.png` in `data/golden/`.
2. Compare extracted keywords against `expected_concepts` → **precision / recall** per screenshot.
3. Compare detected structure vs `expected_hierarchy`.
4. Feed the real feature vectors through `predict_intent` and compare against `true_intent`.
5. Emit `outputs/golden_report.json` + a per-screenshot summary, and drive regression tests.

Start collecting screenshots anytime — the harness will read whatever is in `data/golden/`.

## 7. Content awareness: what a single frame can and cannot prove

`predict_intent` now takes a rule-level content-relevance bias: on-screen
keywords are measured against the user's study concepts (from the knowledge
graph), and the label is promoted to `studying` only when real study content
is visible, or demoted to `passive` when the screen shows nothing relevant
(see `tracker_app/tracking/intent_module.py`).

What the golden data has established so far:

- A genuinely non-study screen (e.g. `009`, a bare file-explorer window) scores
  relevance 0.000 and is demoted correctly.
- A screen whose visible text overlaps the study-concept graph **cannot be told
  apart from studying by content alone** when the overlap comes from context
  the user isn't acting on. Real studying sample `002` (heavily OCR-garbled)
  scores the same relevance as the negatives `009/012/014`, and a semantic
  (embedding) comparison ranks the negatives *above* some genuine studying
  frames. No lexical or semantic threshold separates them without
  misclassifying real studying.
- The focused browser tab is now captured (Windows UIA; pywinauto) and treated
  as ground truth of what the user is engaged with: a non-study tab demotes
  studying to passive even when the screen text overlaps study concepts, a
  study tab promotes passive/idle to studying, and no browser (or a sensitive
  window) keeps the OCR-only behavior. Record `focused_tab_title`/`focused_tab_url`
  in browser-mode labels so the harness can verify this (see
  `tracker_app/tracking/focused_tab.py`).
- Measured effect on the golden set: `014` (Google Careers) is now correctly
  `passive` via the tab signal (`rules+tabs`), intent accuracy 0.80 -> 0.87.
  `012` (Kaggle home) remains a **documented limit**: its tab genuinely matches
  the study concepts (tab_relevance 1.0), so no lexical tab signal can overrule
  the `idle` ground truth.

Keep `true_intent` honest in new samples: a screen that merely shows study
adjacent text while the user is doing something else (job search, browsing a
hub page) should stay `passive`/`idle`, and the runner will report if content
awareness drifts on them.
