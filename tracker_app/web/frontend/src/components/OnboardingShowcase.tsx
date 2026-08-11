import { m, useReducedMotion } from 'motion/react'
import { Link } from 'react-router-dom'
import {
    Play,
    Eye,
    BrainCircuit,
    Network,
    ShieldCheck,
    Activity,
    ArrowRight,
    Sparkles,
} from 'lucide-react'
import { Button } from './ui/button'
import { easeOut } from '@/lib/animation'

const steps = [
    {
        icon: Play,
        step: '01',
        title: 'Start a study session',
        body: 'Flip the toggle. FKT only watches while you study — it idles the rest of the time, and it never touches banking, login or medical windows.',
    },
    {
        icon: Eye,
        step: '02',
        title: 'FKT captures passively',
        body: 'Screen OCR, audio cues and an attention score feed an intent classifier. It recognizes active study and ignores YouTube tabs and chat messages.',
    },
    {
        icon: BrainCircuit,
        step: '03',
        title: 'Review before you forget',
        body: 'Concepts auto-promote into an SM-2 spaced-repetition deck, scheduled for the moment you are about to forget them.',
    },
]

const features = [
    {
        icon: Network,
        title: 'Knowledge Graph',
        body: 'Concepts become graph nodes with live memory scores, co-occurrence edges and drift detection.',
    },
    {
        icon: ShieldCheck,
        title: 'Privacy-first',
        body: 'Sensitive windows are skipped entirely; emails, cards and passwords are redacted before anything is stored.',
    },
    {
        icon: Activity,
        title: 'Attention-aware',
        body: 'Distractions are filtered by the intent gate, so your deck stays a true map of what you studied.',
    },
]

export default function OnboardingShowcase() {
    const reduced = useReducedMotion()

    return (
        <div className="space-y-3">
            {/* HERO */}
            <m.div
                className="relative overflow-hidden border border-border bg-card p-6"
                initial={reduced ? false : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: easeOut }}
            >
                <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-primary/5 blur-3xl" />
                <div className="relative">
                    <div className="mb-3 flex items-center gap-2">
                        <Sparkles size={14} strokeWidth={1.5} className="text-primary" />
                        <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                            Welcome to FKT
                        </span>
                    </div>
                    <h1 className="mb-2 font-mono text-xl font-semibold tracking-tight text-foreground">
                        Your screen becomes your study deck.
                    </h1>
                    <p className="max-w-2xl font-mono text-[12px] leading-relaxed text-muted-foreground">
                        Forgotten Knowledge Tracker passively captures the concepts on your
                        screen while you study, then schedules them with spaced repetition so
                        nothing you read quietly slips away. No manual card entry — just study,
                        and FKT does the rest.
                    </p>
                </div>
            </m.div>

            {/* HOW IT WORKS */}
            <div className="grid grid-cols-4 gap-3">
                {steps.map((s, i) => (
                    <m.div
                        key={s.step}
                        className="flex flex-col border border-border bg-card p-4 transition-colors hover:border-primary/25"
                        initial={reduced ? false : { opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 + i * 0.06, duration: 0.35, ease: easeOut }}
                    >
                        <div className="mb-3 flex items-center justify-between">
                            <s.icon size={16} strokeWidth={1.5} className="text-primary" />
                            <span className="font-mono text-[10px] text-muted-foreground/60">{s.step}</span>
                        </div>
                        <span className="mb-1.5 block text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                            {s.title}
                        </span>
                        <p className="text-[12px] leading-relaxed text-muted-foreground">{s.body}</p>
                    </m.div>
                ))}

                {/* QUICK ACTIONS */}
                <m.div
                    className="flex flex-col justify-between border border-border bg-card p-4 transition-colors hover:border-primary/25"
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.28, duration: 0.35, ease: easeOut }}
                >
                    <div className="mb-3 flex items-center gap-2">
                        <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                            Get started
                        </span>
                        <ArrowRight size={12} className="text-primary" />
                    </div>
                    <div className="flex flex-col gap-2">
                        <Link to="/review">
                            <Button variant="default" size="sm" className="w-full">
                                Open Review deck
                            </Button>
                        </Link>
                        <Link to="/graph">
                            <Button variant="outline" size="sm" className="w-full">
                                Explore the graph
                            </Button>
                        </Link>
                        <Link to="/add">
                            <Button variant="ghost" size="sm" className="w-full">
                                Add a concept manually
                            </Button>
                        </Link>
                    </div>
                </m.div>
            </div>

            {/* FEATURES */}
            <div className="grid grid-cols-3 gap-3">
                {features.map((f, i) => (
                    <m.div
                        key={f.title}
                        className="flex items-start gap-3 border border-border bg-card p-4 transition-colors hover:border-primary/25"
                        initial={reduced ? false : { opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.34 + i * 0.05, duration: 0.35, ease: easeOut }}
                    >
                        <f.icon size={16} strokeWidth={1.5} className="mt-0.5 shrink-0 text-primary" />
                        <div>
                            <span className="mb-1 block text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                                {f.title}
                            </span>
                            <p className="text-[12px] leading-relaxed text-muted-foreground">{f.body}</p>
                        </div>
                    </m.div>
                ))}
            </div>
        </div>
    )
}
