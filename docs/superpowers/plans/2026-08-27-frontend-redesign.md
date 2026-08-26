# Frontend Redesign Implementation Plan (Phases B-H)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Upgrade the FKT frontend from functional-but-static to visually alive, using the existing shadcn/ui + motion + animejs foundation to make real backend data visible and every interaction feel deliberate.

**Architecture:** Enhance existing components in-place — no new pages, no new routes. Each phase targets specific files with targeted visual upgrades: animated counters, Bklit-style charts, glass cards, skeleton loaders, and motion micro-interactions. All animations respect useReducedMotion().

**Tech Stack:** React 18, motion v13 (LazyMotion + domMax), animejs v4, shadcn/ui (new-york), Tailwind CSS v3, TypeScript, Vite 5

**Spec:** FRONTEND_REDESIGN_PLAN.md (root of repo)

## Current State Assessment

Many features described in the spec are **already implemented**:

| Feature | Status | Notes |
|---|---|---|
| shadcn/ui installed | ✅ Done | 5 primitives: button, card, badge, input, skeleton |
| motion installed | ✅ Done | LazyMotion + domMax in App.tsx |
| animejs installed | ✅ Done | Used in ForceGraph.tsx only |
| CSS variable tokens | ✅ Done | Full HSL token system in index.css |
| prefers-reduced-motion | ✅ Done | Global CSS + useReducedMotion() in components |
| Route transitions | ✅ Done | AnimatePresence + pageVariants in App.tsx |
| Nav pill layoutId | ✅ Done | MainLayout.tsx |
| Session toggle glow | ✅ Done | Ambient pulse + press ripple in SessionToggleButton.tsx |
| AnimatedNumber | ✅ Done | Spring-animated counter in StatCard.tsx |
| StreakFlame glow | ✅ Done | Streak-intensity breathing glow |
| Force graph + anime.js settling | ✅ Done | ForceGraph.tsx with hover-to-highlight |
| Trend chart pathLength draw | ✅ Done | TrendChart.tsx |
| Quiz modal scale+fade | ✅ Done | MicroQuizModal.tsx |
| Toast slide+fade | ✅ Done | IntentFeedbackToast.tsx |
| Drift badge animated | ✅ Done | Scale-in + pulsing dot |
| Page skeletons | ✅ Done | Overview, Graph, Quiz skeletons |

**What remains targets specific visual quality gaps, not foundational work.**

---

## Phase D — Graph Page (highest impact)

### Task 1: Bklit-style stat cards for Graph page

**Files:**
- Modify: src/pages/GraphPage.tsx:13-23 (StatChip component)
- Modify: src/pages/GraphPage.tsx:101-109 (stat card grid)

**What to change:** Replace the flat StatChip with a styled card using the existing Card/CardContent shadcn primitives, add an AnimatedNumber for the value, and add a subtle entrance animation with staggered delay.

- [ ] **Step 1: Update StatChip to use AnimatedNumber + motion entrance**

Replace the StatChip function in src/pages/GraphPage.tsx with:

`	sx
import AnimatedNumber from '@/components/AnimatedNumber'
import { m } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import { easeOut } from '@/lib/animation'

function StatChip({ label, value, icon: Icon, delay = 0 }: { label: string; value: number | string; icon: typeof Network; delay?: number }) {
    const reduced = useReducedMotion()
    const numericValue = typeof value === 'number' ? value : parseInt(String(value).replace(/[^0-9]/g, ''), 10)
    return (
        <m.div
            className="border border-border bg-card p-3.5 transition-colors hover:border-primary/20"
            initial={reduced ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: delay * 0.06, duration: 0.3, ease: easeOut }}
        >
            <div className="mb-2 flex items-center gap-1.5">
                <Icon size={11} strokeWidth={1.5} className="text-muted-foreground" />
                <span className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground">{label}</span>
            </div>
            <span className="font-mono text-xl text-foreground">
                {isNaN(numericValue) ? value : <AnimatedNumber value={numericValue} />}
            </span>
        </m.div>
    )
}
`

- [ ] **Step 2: Add stagger delays to the stat grid**

In GraphPage.tsx, update the stat grid to pass delay props:

`	sx
<div className="grid grid-cols-3 gap-3">
    <StatChip label="Concepts" value={stats?.total_concepts ?? 0} icon={Network} delay={0} />
    <StatChip label="Connections" value={stats?.total_edges ?? 0} icon={Share2} delay={1} />
    <StatChip label="Avg Memory" value={stats ? ${(stats.avg_memory_strength * 100).toFixed(0)}% : '0'} icon={AlertTriangle} delay={2} />
</div>
`

- [ ] **Step 3: Verify build**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vite build
Expected: 0 TypeScript errors, build succeeds.

---

### Task 2: Knowledge gaps as animated glass cards

**Files:**
- Modify: src/pages/GraphPage.tsx:154-182 (gaps section)

**What to change:** Replace the plain <ul> list of gaps with Kokonut-style glass cards that use AnimatePresence + layout for staggered entrance. Each card shows the concept name, a memory strength bar, and a "bridge concepts" hint.

- [ ] **Step 1: Replace gap list items with animated cards**

In GraphPage.tsx, replace the gaps <ul> section (lines ~165-180) with:

`	sx
import { AnimatePresence } from 'motion/react'

<AnimatePresence initial={false}>
    {gaps.map((g, i) => (
        <m.div
            key={g.concept}
            layout
            initial={reduced ? false : { opacity: 0, y: 10, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: i * 0.05, duration: 0.25, ease: easeOut }}
            className="border border-border/60 bg-background/50 p-3 backdrop-blur-sm transition-colors hover:border-primary/20"
        >
            <div className="mb-1.5 flex items-baseline justify-between">
                <span className="max-w-[150px] truncate font-mono text-xs text-foreground">{g.concept}</span>
                <span className="ml-2 shrink-0 font-mono text-[10px] text-muted-foreground">
                    {(g.memory_strength * 100).toFixed(0)}%
                </span>
            </div>
            <MemBar v={g.memory_strength} />
            <p className="mt-1 font-mono text-[9px] text-muted-foreground">
                last seen: {g.last_seen ? new Date(g.last_seen).toLocaleDateString() : 'never'}
            </p>
        </m.div>
    ))}
</AnimatePresence>
`

- [ ] **Step 2: Wrap gaps section in a container with reduced import**

Add const reduced = useReducedMotion() to GraphPage if not already present (it's needed for the gap cards). Import AnimatePresence from motion/react at the top.

- [ ] **Step 3: Verify build**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vite build

---

## Phase C — Overview Page

### Task 3: Enhanced trend chart with Bklit-style area fill

**Files:**
- Modify: src/components/TrendChart.tsx

**What to change:** The TrendChart already has a pathLength draw-on animation. Enhance it with: (1) a gradient fill that animates opacity on mount, (2) hover tooltip showing the exact value for each data point, (3) subtle grid lines for readability.

- [ ] **Step 1: Add gradient opacity animation and grid lines**

Update TrendChart.tsx to include:
- A <defs> block with a linear gradient fill (primary color to transparent)
- Grid lines rendered as thin horizontal <line> elements at 25%/50%/75% height
- The gradient <path> fading in with initial={{ opacity: 0 }} / nimate={{ opacity: 1 }}

- [ ] **Step 2: Add hover tooltip**

Add a useState<number | null>(hoveredIdx) and render a <m.div> tooltip that appears on onMouseMove over the SVG, showing the exact value for that data point. Use the existing spring transition for the tooltip position.

- [ ] **Step 3: Verify build + existing tests pass**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vitest run

---

### Task 4: Due-today list AnimatePresence improvements

**Files:**
- Modify: src/pages/OverviewPage.tsx:221-261 (due today section)

**What to change:** The due-today list already uses AnimatePresence + layout. Enhance with: (1) a sliding exit animation when items are reviewed (already partially there), (2) a "reviewed" checkmark animation on exit, (3) a count-up animation for the "Due Today · N" header.

- [ ] **Step 1: Add reviewed checkmark exit animation**

Update the due-today exit animation to slide left with a brief green flash:

`	sx
exit={reduced ? undefined : { opacity: 0, x: -20, transition: { duration: 0.3 } }}
`

- [ ] **Step 2: Animated count in panel title**

Replace the static Due Today ·  with an AnimatedNumber:

`	sx
{panelTitle('Due Today')}<span className="ml-2 font-mono text-[10px] text-primary"><AnimatedNumber value={dueItems.length} /></span>
`

- [ ] **Step 3: Verify build**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vite build

---

## Phase E — Quiz Experience

### Task 5: Answer feedback animations (checkmark/shake)

**Files:**
- Modify: src/components/QuizOptionList.tsx
- Modify: src/components/FlashcardView.tsx
- Modify: src/components/FillBlankView.tsx

**What to change:** When the user answers correctly, briefly flash the option green with an SVG checkmark path animation. When incorrect, shake the option and flash red. Use Motion's pathLength for the checkmark, and a keyframe shake for incorrect.

- [ ] **Step 1: Add answer feedback state to QuizOptionList**

In QuizOptionList.tsx, add a eedbackState that tracks {index: 'correct' | 'incorrect' | null}. When onAnswer fires, set the state for 800ms then clear it.

- [ ] **Step 2: Add correct/incorrect visual feedback**

For the correct option: wrap in <m.div animate={feedback === 'correct' ? { backgroundColor: 'rgba(0,255,163,0.15)' } : {}}> and show an SVG checkmark with <m.path initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} />.

For the incorrect option: use <m.div animate={feedback === 'incorrect' ? { x: [0, -4, 4, -4, 4, 0] } : {}}> for a brief shake.

- [ ] **Step 3: Apply same pattern to FlashcardView and FillBlankView**

Add the same feedback state and visual treatment to both quiz type components.

- [ ] **Step 4: Verify build + tests**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vitest run

---

### Task 6: Quiz difficulty badge color upgrade

**Files:**
- Modify: src/components/DifficultyBadge.tsx

**What to change:** Add color-coded backgrounds for easy (green tint), medium (amber tint), hard (red tint) with a subtle entrance animation.

- [ ] **Step 1: Add color variants and scale-in animation**

`	sx
const colors: Record<string, string> = {
    easy: 'border-primary/40 bg-primary/10 text-primary',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-500',
    hard: 'border-destructive/40 bg-destructive/10 text-destructive',
}
`

Wrap in <m.span initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>.

- [ ] **Step 2: Verify build**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vite build

---

## Phase B — Shell

### Task 7: Collapse/expand animation improvement

**Files:**
- Modify: src/layouts/MainLayout.tsx

**What to change:** The sidebar collapse/expand should use a spring transition for width instead of an instant CSS toggle. Also ensure the nav pill layoutId animation is smooth during collapse.

- [ ] **Step 1: Add spring transition to sidebar width**

In MainLayout.tsx, replace the conditional width class with a motion.aside that animates width between 48px (collapsed) and 200px (expanded) using the shared spring transition.

- [ ] **Step 2: Verify nav pill stays smooth during collapse**

Ensure the layoutId="nav-pill" indicator animates correctly when the sidebar transitions between states.

- [ ] **Step 3: Verify build + tests**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vitest run

---

## Phase F — Intent Feedback Toast

### Task 8: Toast entrance polish (already mostly done)

**Files:**
- Verify: src/components/IntentFeedbackToast.tsx

**What to change:** The toast already has slide+fade entrance/exit. Verify it matches the Kokonut style (slide from right + slight scale). If not, update the entrance variant to include scale: 0.96 -> 1.

- [ ] **Step 1: Verify current animation matches spec**

Read IntentFeedbackToast.tsx and confirm the entrance uses slide + fade + optional scale. If scale is missing, add it to the motion variant.

- [ ] **Step 2: Verify build**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vite build

---

## Phase G — Review / Knowledge Base / Add Concept Pages

### Task 9: Card-based list layout for Review and Knowledge Base

**Files:**
- Modify: src/pages/ReviewPage.tsx
- Modify: src/pages/KnowledgeBasePage.tsx

**What to change:** Replace flat row layouts with card-based items using the existing Card shadcn primitive. Add hover-lift effect (whileHover={{ y: -2 }}) and glass-style background. Wrap item lists in AnimatePresence + layout for smooth add/remove transitions.

- [ ] **Step 1: Update ReviewPage items to card layout**

Replace row <div>s with <Card> elements, add hover-lift motion, wrap in AnimatePresence.

- [ ] **Step 2: Update KnowledgeBasePage items to card layout**

Same treatment: card wrapper, hover-lift, AnimatePresence for list transitions.

- [ ] **Step 3: Add animated search bar to KnowledgeBasePage**

Replace the static search <input> with a motion-wrapped input that expands on focus:

`	sx
<m.div animate={{ width: focused ? '100%' : '75%' }} transition={spring}>
    <Input ... />
</m.div>
`

- [ ] **Step 4: Verify build + tests**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vitest run

---

## Phase H — Loading & Empty States

### Task 10: Enhanced skeleton loaders

**Files:**
- Modify: src/components/PageSkeleton.tsx

**What to change:** Upgrade existing skeletons to be more content-shaped. Add a subtle shimmer animation direction change. Make skeleton shapes match actual content layouts more closely.

- [ ] **Step 1: Enhance OverviewSkeleton**

Make the skeleton KPI cards match the exact StatCard dimensions. Add a skeleton chart area that matches TrendChart shape. Add skeleton rows for the due-today list.

- [ ] **Step 2: Enhance GraphSkeleton**

Add skeleton node circles in the graph area (3-5 circles of varying sizes) to hint at the force-graph that's loading.

- [ ] **Step 3: Enhance QuizSkeleton**

Add a skeleton question text area and skeleton option bars that match the actual quiz layout.

- [ ] **Step 4: Verify build + tests**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vitest run

---

### Task 11: Backend-down state upgrade

**Files:**
- Modify: src/components/BackendDown.tsx

**What to change:** Replace the generic error message with a calmer, on-brand illustration — a blinking cursor / "connection lost" motif consistent with the terminal aesthetic.

- [ ] **Step 1: Redesign BackendDown with terminal aesthetic**

`	sx
export default function BackendDown() {
    return (
        <div className="flex h-64 flex-col items-center justify-center gap-4">
            <div className="font-mono text-sm text-muted-foreground">
                <m.span
                    animate={{ opacity: [1, 0, 1] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                >
                    _
                </m.span>
            </div>
            <div className="text-center">
                <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                    connection lost
                </p>
                <p className="mt-1 font-mono text-[10px] text-muted-foreground/60">
                    flask api unreachable — check if the backend is running
                </p>
            </div>
        </div>
    )
}
`

- [ ] **Step 2: Verify build**

Run: cd tracker_app/web/frontend && npx tsc --noEmit && npx vite build

---

## Verification

After all tasks are complete:

- [ ] Run full TypeScript check: cd tracker_app/web/frontend && npx tsc --noEmit
- [ ] Run all frontend tests: cd tracker_app/web/frontend && npx vitest run
- [ ] Run production build: cd tracker_app/web/frontend && npx vite build
- [ ] Run ruff check: cd tracker_app/web/frontend/../../.. && python -m ruff check tracker_app/
- [ ] Run ruff format check: cd tracker_app/web/frontend/../../.. && python -m ruff format --check tracker_app/
- [ ] Manual test: start the app and verify each page visually