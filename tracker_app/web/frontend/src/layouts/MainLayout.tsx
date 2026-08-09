import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { m, AnimatePresence, useReducedMotion } from 'motion/react'
import { Home, Activity, Database, PlusCircle, Search, Share2, Zap, ChevronLeft } from 'lucide-react'
import IntentFeedbackToast from '../components/IntentFeedbackToast'
import MicroQuizModal from '../components/MicroQuizModal'
import SessionToggleButton from '../components/SessionToggleButton'
import { useSession } from '../context/SessionContext'
import { spring, pageVariants, pageTransition } from '../lib/animation'
import { cn } from '../lib/utils'

const navItems = [
    { id: '', icon: Home, label: 'Overview' },
    { id: 'review', icon: Activity, label: 'Review Session' },
    { id: 'database', icon: Database, label: 'Knowledge Base' },
    { id: 'graph', icon: Share2, label: 'Knowledge Graph' },
    { id: 'quiz', icon: Zap, label: 'Micro-Quiz' },
    { id: 'add', icon: PlusCircle, label: 'Add Concept' },
]

function SessionIndicator() {
    const { active } = useSession()
    return (
        <span
            className={cn(
                'flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest',
                active ? 'text-primary' : 'text-muted-foreground'
            )}
            title={active ? 'Study session active — capturing concepts' : 'No active study session'}
        >
            <m.span
                className={cn('h-1.5 w-1.5', active ? 'bg-primary' : 'bg-muted-foreground')}
                animate={active ? { opacity: [1, 0.25, 1] } : { opacity: 1 }}
                transition={active ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' } : { duration: 0 }}
            />
            {active ? 'Capturing' : 'Idle'}
        </span>
    )
}

function Sidebar() {
    const reduced = useReducedMotion()
    const [pinned, setPinned] = useState(false)
    const [hovered, setHovered] = useState(false)
    const wide = pinned || hovered

    return (
        <m.aside
            className="fixed left-0 top-0 z-50 flex h-full flex-col overflow-hidden border-r border-border bg-card py-4"
            animate={{ width: wide ? 200 : 48 }}
            transition={reduced ? { duration: 0 } : spring}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
        >
            <div className="mb-6 flex h-[32px] shrink-0 items-center justify-between px-3">
                <span className={cn('whitespace-nowrap font-mono text-xs font-bold text-primary', !wide && 'opacity-0')}>
                    FKT
                </span>
                <button
                    onClick={() => setPinned(p => !p)}
                    title={pinned ? 'Unpin sidebar' : 'Pin sidebar'}
                    className={cn('text-muted-foreground transition-colors hover:text-foreground', !wide && 'hidden')}
                >
                    <m.span animate={{ rotate: pinned ? 180 : 0 }} transition={spring}>
                        <ChevronLeft size={14} />
                    </m.span>
                </button>
            </div>

            <nav className="flex w-full flex-col space-y-1 px-2">
                {navItems.map((item) => (
                    <NavLink
                        key={item.id}
                        to={`/${item.id}`}
                        end={item.id === ''}
                        className="relative flex w-full items-center px-2 py-2.5"
                    >
                        {({ isActive }) => (
                            <>
                                {isActive && (
                                    <m.span
                                        layoutId="nav-pill"
                                        className="absolute inset-0 border border-primary/20 bg-secondary"
                                        transition={reduced ? { duration: 0 } : spring}
                                    />
                                )}
                                <item.icon
                                    size={18}
                                    strokeWidth={1.5}
                                    className={cn(
                                        'relative min-w-[20px] transition-colors',
                                        isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                                    )}
                                />
                                <span
                                    className={cn(
                                        'relative ml-4 whitespace-nowrap text-[10px] font-semibold uppercase tracking-[0.12em]',
                                        isActive ? 'text-primary' : 'text-muted-foreground',
                                        !wide && 'opacity-0'
                                    )}
                                >
                                    {item.label}
                                </span>
                            </>
                        )}
                    </NavLink>
                ))}
            </nav>
        </m.aside>
    )
}

export default function MainLayout() {
    const location = useLocation()
    const reduced = useReducedMotion()
    const { active } = useSession()

    useEffect(() => {
        document.title = 'FKT Dashboard'
    }, [])

    return (
        <div className="flex min-h-screen overflow-hidden bg-background font-sans text-muted-foreground">
            <svg className="hidden">
                <defs>
                    <linearGradient id="accentGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00FFA3" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#00FFA3" stopOpacity={0} />
                    </linearGradient>
                </defs>
            </svg>

            <Sidebar />

            <main className="ml-[48px] flex h-screen w-full flex-1 flex-col overflow-y-auto">
                <header className="sticky top-0 z-40 flex h-[48px] shrink-0 items-center justify-between border-b border-border bg-background/90 px-6 backdrop-blur-sm">
                    <span className="font-mono text-xs uppercase tracking-widest text-foreground">
                        SYS_MONITOR <span className="text-muted-foreground">// FKT v2.0</span>
                    </span>
                    <div className="flex items-center gap-4">
                        <SessionToggleButton size="sm" />
                        <SessionIndicator />
                        <Search size={14} strokeWidth={1.5} />
                        <span className="font-mono text-[11px]">CMD+K</span>
                        <m.div
                            className="h-1.5 w-1.5 bg-primary"
                            title="System Online"
                            animate={active ? { opacity: [1, 0.3, 1] } : { opacity: 1 }}
                            transition={active ? { duration: 1.6, repeat: Infinity } : { duration: 0 }}
                        />
                    </div>
                </header>

                <div className="flex-1 p-5">
                    <AnimatePresence mode="wait" initial={false}>
                        <m.div
                            key={location.pathname}
                            variants={pageVariants}
                            initial={reduced ? false : 'initial'}
                            animate="animate"
                            exit={reduced ? undefined : 'exit'}
                            transition={pageTransition}
                        >
                            <Outlet />
                        </m.div>
                    </AnimatePresence>
                </div>
            </main>

            {/* Global floating feedback prompt */}
            <IntentFeedbackToast />

            {/* Live-pushed micro-quiz interrupt */}
            <MicroQuizModal />
        </div>
    )
}
