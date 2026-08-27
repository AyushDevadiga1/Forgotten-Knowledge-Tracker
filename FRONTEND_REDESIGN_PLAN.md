# FKT Frontend Redesign Plan

**Why this exists:** the backend is now doing genuinely correct, live work (real memory scores, real feedback pipeline, real drift/gap detection) — but the current frontend is a static, mostly-unanimated Tailwind shell that doesn't make any of that feel alive. This plan rebuilds the frontend on a proper component + animation foundation, inspired by four references chosen deliberately, not just for polish:

| Reference | What it actually is | What FKT takes from it |
|---|---|---|
| **[Bklit UI](https://bklit.com)** *(primary influence)* | A shadcn/ui chart registry built on d3/visx + Motion — GeistSans type, 8px grid, minimal dark data-viz aesthetic, "design engineered" charts | The entire Overview/Graph page visual language. FKT is a data product; it should look like one. |
| **[Kokonut UI](https://kokonutui.com)** | shadcn/ui + Tailwind + Motion component collection — glass cards, particle buttons, animated text, animated backgrounds, smooth modals/toasts | Micro-interactions: the quiz modal, session toggle, feedback toast, empty/loading states |
| **[Motion](https://motion.dev)** *(formerly Framer Motion)* | The React animation engine both of the above are built on | The actual animation runtime for the whole app — layout transitions, gestures, `AnimatePresence` |
| **[anime.js](https://animejs.com)** | Lightweight vanilla JS animation engine — timelines, SVG path morphing, stagger | Reserved for exactly one thing: the knowledge-graph visualization, where Motion's declarative model is the wrong tool |

**Important constraint carried over from every prior phase of this project:** this runs *during study sessions*. Anything animated has to pass the same "humanly proper" bar the notification work did — delightful, never distracting, and fully respecting `prefers-reduced-motion`. This is not a marketing site.

## Phase A — Foundation (do this before touching any page)

Everything below depends on getting this right first; skipping ahead to page redesigns on the old foundation means redoing the work twice.

- [ ] **Adopt shadcn/ui as the primitive layer.** Both Bklit UI and Kokonut UI are shadcn registries — components install via `npx shadcn@latest add <component>` directly into the codebase (not an npm dependency, so FKT owns and can modify every line, consistent with how the rest of this codebase has been treated). Run `npx shadcn@latest init` against the existing Vite + Tailwind + TS setup.
- [ ] **Install `motion` (`npm install motion`)** as the one animation runtime for the whole app. Use `LazyMotion` + the `domAnimation` feature bundle rather than the full `motion/react` import everywhere — keeps bundle size down, matters for a Vite app that's meant to start fast.
- [ ] **Rebuild FKT's existing dark/monospace/terminal identity as proper shadcn CSS-variable tokens**, not a replacement of it. The current `fkt-accent` / `fkt-surface` / `fkt-elevated` palette and monospace-for-numbers convention is a genuinely distinctive, good aesthetic — keep it, just express it the way shadcn/Bklit/Kokonut components expect (`--background`, `--primary`, `--radius`, etc. in `globals.css`) so every borrowed component inherits FKT's look automatically instead of arriving in its own default light-SaaS styling that then needs manual overriding per-component.
- [ ] **Add `animejs` as a scoped dependency used in exactly one place** (the graph — Phase D below). Do not let it spread into general UI animation; that's Motion's job. Two animation engines doing overlapping work is worse than one, even a good one twice.
- [ ] **Wire `prefers-reduced-motion` globally.** Motion respects it automatically for most transition types via `useReducedMotion()` — use that hook at the layout level to drop transform/spring animations to instant or fade-only app-wide when the OS setting is on. Non-negotiable given this app runs during focus time.
- [ ] **Global route transitions.** Wrap the router outlet in `AnimatePresence` with a short fade+slight-slide between Overview/Review/Graph/Quiz/Knowledge Base — currently navigation hard-cuts.

## Phase B — Shell (`MainLayout.tsx`)

- [ ] **Sidebar nav**: replace the static active-link style with a Motion `layoutId` shared-element indicator — a pill/underline that physically slides and morphs to the new active item on navigation, rather than each link independently toggling a class. This is the single highest-value, lowest-effort animation in the whole app (Motion's signature move, one prop).
- [ ] **Session toggle (Start/Stop Studying)**: this button is the most important control in the app — it's the whole Phase 9 relevance fix made visible. Give it real state weight: a Kokonut-style animated toggle with a soft pulsing glow while a session is active (reinforces "FKT is watching right now" at a glance, which also serves the earlier "is this humanly proper" concern — the user should never have to wonder if it's on), and a satisfying ripple/press animation on click. Pair with the existing `SessionIndicator` rather than replacing it.
- [ ] **Collapse/expand**: animate width + icon-only collapse with a spring transition instead of an instant CSS toggle, if not already smooth.

## Phase C — Overview page

The backend now has a real trend endpoint (`GET /stats/trend`) and real per-concept memory scores — this page should finally be able to show honest, live data instead of static numbers.

- [ ] **Replace flat stat numbers with Bklit-style animated counters** — count up from 0 on mount/update rather than snapping to the new value. Small, but it's the detail that makes a dashboard feel alive rather than static.
- [ ] **Real trend charts**: pull in a Bklit UI line/area chart component for the review-trend and memory-score-trend data now that it's backed by real numbers, not the old fabricated `miniSparkline()`. Bklit's chart components already handle the d3/visx + Motion wiring, so this is largely composition, not custom charting code.
- [ ] **Streak display**: a small animated flame/glow that visually intensifies with streak length (Kokonut animated-icon pattern) — gives the existing streak number some emotional weight without adding a new metric.
- [ ] **Due-today list**: animate items in/out with `AnimatePresence` + `layout` as items move from "due" to "reviewed" during a session, instead of the list just re-rendering.

## Phase D — Graph page (highest-impact page in the whole redesign)

This page was flagged in the backend audit as rendering a fake spoke diagram with a hardcoded "HUB" node that ignored real edge data; that's since been fixed to draw genuine weighted edges, and `memory_score` per node is now live (Phase 11.2). The current frontend has no visualization capable of showing any of that off. This is where the effort belongs.

- [ ] **Real force-directed layout, animated with anime.js** — the one place in this plan that isn't Motion. Nodes sized/colored by live `memory_score` (weak concepts visually read as "weak" — dim/small; strong ones bright/large), edges drawn with opacity/thickness scaled by weight, physics-based settling animation on load (anime.js timeline + stagger for node entrance), smooth hover-to-highlight-neighbors, click to drill into `get_concept_history()`.
- [ ] **Bklit-style stat cards alongside the graph**: avg memory score trend, node/edge count over time, rather than the graph sitting alone with no supporting context.
- [ ] **Knowledge-gap suggestions as an animated card list** (Kokonut glass-card or flip-card style) instead of a plain list — each gap suggestion names its two bridge concepts, which is naturally a small, visually interesting "here's the connection" card rather than a text row.
- [ ] **Concept drift indicator**: now that `/graph/drift/<concept>` returns real `new`/`stagnant`/`evolving`/`stable` status (Phase 11.3/11.4), give each of those a distinct small animated badge rather than plain text — this is exactly the kind of state-driven micro-animation Kokonut's component set is built for.

## Phase E — Quiz experience (`QuizPage.tsx` + `MicroQuizModal.tsx`)

- [ ] **Modal entrance**: Kokonut-style scale+fade spring entrance instead of an instant appear — this is the app's "interrupt," it should feel considered, not jarring (ties back to the 10.3 timing fix: now that it only fires at a good moment, it should also *look* like a deliberate, calm interruption rather than a pop-up).
- [ ] **Answer feedback**: correct answer draws a checkmark via an SVG path animation (anime.js or Motion's `pathLength` — Motion is sufficient here, no need to reach for anime.js again); incorrect gets a brief shake + red flash. Small, immediate, satisfying feedback loop — this is standard spaced-repetition-app practice (Duolingo, Anki mobile) for good reason: it makes review feel rewarding rather than clinical.
- [ ] **Difficulty badge**: `quiz_engine.py` already returns `difficulty: easy|medium|hard` — currently likely unused or plain text in the UI; give it a small color-coded animated badge.
- [ ] **Shared logic stays shared**: the existing `useQuizAnswer` hook and `QuizResultBanner` (already extracted to avoid duplication between the page and the modal) should keep being the single source of this behavior — add the animation inside those shared pieces, not duplicated per-component again.

## Phase F — Intent feedback toast (light touch — the substance is already fixed)

10.1 and 10.4 already fixed the mechanics and content (cooldown, dismissal, timestamp, window context, warmer "Quick Check" framing). This phase is purely the animation layer on top of already-correct behavior:

- [ ] Kokonut-style slide+fade entrance/exit instead of the current instant appear/disappear.
- [ ] Nothing else — resist the urge to re-litigate the copy/tone again here; that's settled.

## Phase G — Review / Knowledge Base / Add Concept pages

Lower priority than C–E (Graph and Quiz are where the backend's real work is currently invisible), but for consistency once the foundation is in:

- [ ] Card-based list layout with Kokonut hover-lift/glass effects instead of flat rows.
- [ ] `AnimatePresence` + `layout` for items entering/leaving as they're reviewed, archived, or added — same pattern as the Overview due-list.
- [ ] Animated search bar on Knowledge Base (Kokonut has a ready component for this).

## Phase H — Loading & empty states

Phase 3 already built empty/loading/backend-down states for Graph and Quiz — this phase is upgrading their visual quality, not building them from scratch.

- [ ] Replace generic spinners with Kokonut-style skeleton loaders shaped like the content that's about to appear (a skeleton chart shape for the trend, skeleton nodes for the graph) — reduces perceived load time and looks considered rather than default.
- [ ] Backend-down state gets a calmer, on-brand illustration/animation rather than a bare error message, consistent with the terminal aesthetic (e.g. a blinking cursor / "connection lost" motif rather than a generic red banner).

---

## Suggested order of execution

Phase A is not optional and blocks everything else. After that, prioritize by where the backend has real data with no frontend to show it: **D (Graph) and C (Overview charts) first** — that's where months of backend correctness work (Phase 11) is currently invisible to anyone using the app. **E (Quiz)** next, since it's the most-used interactive surface. **B (Shell)** can happen in parallel with any of the above since it's foundational chrome. **F, G, H** are polish passes, correctly last.

## What this plan deliberately does not do

- **No animation for its own sake.** Every item above ties to either making real (now-correct) data visible, or reinforcing a behavior this project already decided mattered (session-state clarity, calm quiz timing, warm toast tone). If a future addition doesn't trace back to one of those, it doesn't belong here.
- **No swapping the visual identity.** FKT's dark/monospace/terminal look stays; Bklit and Kokonut are sources of *components and motion patterns*, not a new color palette or typeface direction.
- **No animating anything during the actual OCR/audio/webcam capture indicators in a way that could be distracting while the user is trying to concentrate.** The session toggle's glow (Phase B) is the one deliberate exception, and it's a slow, ambient pulse, not attention-grabbing motion.

**Status: Complete** — Phase A foundation + Phases B–H all implemented (see docs/superpowers/plans/2026-08-27-frontend-redesign.md).
