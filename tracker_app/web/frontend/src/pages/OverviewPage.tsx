import { useEffect, useState, useCallback } from 'react'
import { m, AnimatePresence, useReducedMotion } from 'motion/react'
import { Search, AlertTriangle, Activity, Database } from 'lucide-react'
import { api, Stats, LearningItem, TrendDay } from '../api'
import { useSession } from '../context/SessionContext'
import StatCard from '../components/StatCard'
import TrendChart from '../components/TrendChart'
import StreakFlame from '../components/StreakFlame'
import SessionToggleButton from '../components/SessionToggleButton'
import { OverviewSkeleton } from '../components/PageSkeleton'
import { formatNumber, formatPercent } from '../lib/format'
import { easeOut } from '../lib/animation'
import { cn } from '../lib/utils'

const statusColor: Record<string, string> = {
    healthy: 'bg-primary',
    warning: 'bg-amber-500',
    critical: 'bg-destructive',
}

function panelTitle(children: React.ReactNode) {
    return <span className="mb-4 block text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{children}</span>
}

export default function OverviewPage() {
    const { active } = useSession()
    const reduced = useReducedMotion()
    const [stats, setStats] = useState<Stats | null>(null)
    const [today, setToday] = useState<{ reviews_today: number; concepts_studied: number } | null>(null)
    const [recentItems, setRecentItems] = useState<LearningItem[]>([])
    const [dueItems, setDueItems] = useState<LearningItem[]>([])
    const [trend, setTrend] = useState<TrendDay[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const load = useCallback(async () => {
        try {
            const [statsRes, itemsRes, trendRes, dueRes] = await Promise.all([
                api.getStats(),
                api.getItems('active', 6),
                api.getStatsTrend(14).catch(() => ({ data: [] as TrendDay[] })),
                api.getDueItems(),
            ])
            setStats(statsRes.data.stats)
            setToday(statsRes.data.today)
            setRecentItems(itemsRes.data)
            setTrend(trendRes.data)
            setDueItems(dueRes.data)
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load data')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        load()
        const poll = setInterval(load, 20000)
        return () => clearInterval(poll)
    }, [load])

    if (loading) return <OverviewSkeleton />

    if (error) return (
        <div className="flex h-64 items-center justify-center gap-3 text-destructive">
            <AlertTriangle size={18} strokeWidth={1.5} />
            <span className="font-mono text-xs">Backend offline — {error}</span>
        </div>
    )

    const kpi = stats
        ? [
              {
                  title: 'TOTAL ITEMS',
                  value: stats.total_items,
                  format: formatNumber,
                  delta: `${stats.active_items} active`,
                  up: true,
                  spark: trend.map((d) => ({ v: d.added })),
              },
              {
                  title: 'MASTERED',
                  value: stats.mastered_items,
                  format: formatNumber,
                  delta: `${Math.round((stats.mastered_items / Math.max(stats.total_items, 1)) * 100)}%`,
                  up: true,
                  spark: trend.map((d) => ({ v: d.mastered })),
              },
              {
                  title: 'AVG SUCCESS',
                  value: stats.average_success_rate,
                  format: formatPercent,
                  delta: `${stats.total_reviews} total reviews`,
                  up: stats.average_success_rate >= 70,
                  spark: trend.map((d) => ({ v: d.accuracy })),
              },
              {
                  title: 'DUE TODAY',
                  value: stats.items_due_today,
                  format: formatNumber,
                  delta: `${today?.reviews_today ?? 0} reviewed`,
                  up: stats.items_due_today === 0,
                  spark: trend.map((d) => ({ v: d.due })),
              },
          ]
        : []

    const trendTotal = trend.reduce((s, d) => s + d.reviews, 0)
    const trendAccuracy = trend.length
        ? Math.round(trend.reduce((s, d) => s + d.accuracy, 0) / trend.length)
        : 0

    return (
        <div className="space-y-3">
            {/* STUDY SESSION CONTROL */}
            <m.div
                className="flex items-center justify-between border border-border bg-card p-4 transition-colors hover:border-primary/25"
                initial={reduced ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: easeOut }}
            >
                <div>
                    <div className="mb-1 flex items-center gap-2">
                        <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Study Session</span>
                        <m.span
                            className={cn('h-2 w-2', active ? 'bg-primary' : 'bg-muted-foreground')}
                            animate={active ? { opacity: [1, 0.3, 1] } : { opacity: 1 }}
                            transition={active ? { duration: 1.6, repeat: Infinity } : { duration: 0 }}
                        />
                    </div>
                    <span className="block text-[12px] text-muted-foreground">
                        FKT captures concepts only while a study session is active — you tell it when.
                    </span>
                </div>
                <SessionToggleButton />
            </m.div>

            {/* KPI CARDS */}
            <div className="grid grid-cols-4 gap-3">
                {kpi.map((k, i) => (
                    <StatCard
                        key={k.title}
                        title={k.title}
                        value={k.value}
                        format={k.format}
                        delta={k.delta}
                        up={k.up}
                        spark={k.spark}
                        delay={i * 60}
                    />
                ))}
            </div>

            {/* MAIN CHART + DUE LIST + SYSTEM STATUS */}
            <div className="grid grid-cols-4 gap-3">
                {/* REVIEW TREND (real /stats/trend) */}
                <m.div
                    className="col-span-2 row-span-2 flex flex-col border border-border bg-card p-4 transition-colors hover:border-primary/25"
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.18, duration: 0.35, ease: easeOut }}
                >
                    <div className="mb-4 flex items-center justify-between">
                        <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                            Review Trend — last {trend.length} days
                        </span>
                        <span className="font-mono text-[10px] text-primary">LIVE</span>
                    </div>
                    <div className="flex min-h-[200px] flex-1 flex-col">
                        <TrendChart data={trend.map((d) => ({ v: d.reviews }))} height={160} />
                        <div className="mt-3 flex gap-6 font-mono text-[10px] text-muted-foreground">
                            <span>
                                Σ <span className="text-primary">{formatNumber(trendTotal)}</span> reviews
                            </span>
                            <span>
                                avg <span className="text-primary">{trendAccuracy}%</span> accuracy
                            </span>
                            <span>
                                peak <span className="text-primary">{formatNumber(Math.max(...trend.map((d) => d.reviews), 0))}</span>/day
                            </span>
                        </div>
                    </div>
                </m.div>

                {/* DUE TODAY — AnimatePresence + layout */}
                <m.div
                    className="col-span-1 row-span-2 flex flex-col border border-border bg-card p-4 transition-colors hover:border-primary/25"
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.24, duration: 0.35, ease: easeOut }}
                >
                    {panelTitle(`Due Today · ${dueItems.length}`)}
                    <div className="flex flex-1 flex-col overflow-auto">
                        {dueItems.length === 0 && (
                            <span className="py-4 text-center font-mono text-xs text-muted-foreground">
                                No items due — memory up to date
                            </span>
                        )}
                        <AnimatePresence initial={false}>
                            {dueItems.map((item) => (
                                <m.div
                                    key={item.id}
                                    layout
                                    initial={reduced ? false : { opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={reduced ? undefined : { opacity: 0, x: -14 }}
                                    transition={{ duration: 0.2, ease: easeOut }}
                                    className="flex items-center justify-between border-b border-border/40 py-2.5 last:border-0"
                                >
                                    <span className="truncate text-[12px] text-foreground" title={item.question}>
                                        {item.question}
                                    </span>
                                    <span
                                        className={cn(
                                            'ml-2 shrink-0 font-mono text-[10px]',
                                            item.success_rate >= 80 ? 'text-primary' : 'text-amber-500'
                                        )}
                                    >
                                        {Math.round(item.success_rate)}%
                                    </span>
                                </m.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </m.div>

                {/* SYSTEM STATUS */}
                <m.div
                    className="col-span-1 flex flex-col border border-border bg-card p-4 transition-colors hover:border-primary/25"
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.35, ease: easeOut }}
                >
                    {panelTitle('System Status')}
                    <div className="flex flex-col gap-2">
                        {[
                            { svc: 'Flask API', status: 'healthy', lat: ':5000' },
                            { svc: 'SQLite DB', status: stats ? 'healthy' : 'critical', lat: 'local' },
                            { svc: 'SM-2 Scheduler', status: (stats?.items_due_today ?? 0) > 50 ? 'warning' : 'healthy', lat: `${stats?.items_due_today ?? 0} due` },
                            { svc: 'Background Tracker', status: active ? 'healthy' : 'warning', lat: active ? 'capturing' : 'idle — Start Studying' },
                        ].map((h, i) => (
                            <div key={i} className="flex items-center justify-between border border-border bg-background p-2">
                                <div className="flex items-center gap-2">
                                    <div className={cn('h-1.5 w-1.5', statusColor[h.status])} />
                                    <span className="text-[12px] text-foreground">{h.svc}</span>
                                </div>
                                <span className="font-mono text-[10px] text-muted-foreground">{h.lat}</span>
                            </div>
                        ))}
                    </div>
                </m.div>
            </div>

            {/* RECENT ITEMS + DATA BREAKDOWN */}
            <div className="grid grid-cols-4 gap-3">
                <m.div
                    className="col-span-2 flex flex-col border border-border bg-card p-4 transition-colors hover:border-primary/25"
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.36, duration: 0.35, ease: easeOut }}
                >
                    <div className="mb-3 flex items-center justify-between">
                        {panelTitle('Recent Items')}
                        <Search size={12} className="text-muted-foreground" />
                    </div>
                    <div className="flex flex-col text-[12px]">
                        {recentItems.length === 0 && (
                            <span className="py-4 text-center font-mono text-xs text-muted-foreground">No items yet</span>
                        )}
                        {recentItems.map((item) => (
                            <div
                                key={item.id}
                                className="flex items-center justify-between border-b border-border/30 px-2 py-2.5 last:border-0 hover:bg-muted"
                            >
                                <span className="truncate text-foreground" title={item.question}>
                                    {item.question}
                                </span>
                                <span
                                    className={cn(
                                        'shrink-0 font-mono text-[10px]',
                                        item.success_rate >= 80 ? 'text-primary' : 'text-amber-500'
                                    )}
                                >
                                    {Math.round(item.success_rate)}%
                                </span>
                            </div>
                        ))}
                    </div>
                </m.div>

                <m.div
                    className="col-span-2 flex flex-col border border-border bg-card p-4 transition-colors hover:border-primary/25"
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.42, duration: 0.35, ease: easeOut }}
                >
                    <div className="mb-4 flex items-center justify-between">
                        {panelTitle('Data Breakdown')}
                        <span className="font-mono text-[10px] text-primary">LIVE</span>
                    </div>
                    <div className="grid flex-1 grid-cols-3 gap-px bg-border text-center">
                        <div className="flex flex-col items-center justify-center gap-2 bg-card p-3">
                            <StreakFlame streak={stats?.current_streak ?? 0} />
                            <span className="font-mono text-lg leading-none text-primary">
                                {(stats?.current_streak ?? 0).toLocaleString()}d
                            </span>
                            <span className="text-[9px] uppercase tracking-widest text-muted-foreground">Streak</span>
                        </div>
                        <div className="flex flex-col items-center justify-center gap-2 bg-card p-3">
                            <Activity size={18} strokeWidth={1.5} className="text-muted-foreground" />
                            <span className="font-mono text-lg leading-none text-primary">
                                {(stats?.total_reviews ?? 0).toLocaleString()}
                            </span>
                            <span className="text-[9px] uppercase tracking-widest text-muted-foreground">Reviews</span>
                        </div>
                        <div className="flex flex-col items-center justify-center gap-2 bg-card p-3">
                            <Database size={18} strokeWidth={1.5} className="text-muted-foreground" />
                            <span className="font-mono text-lg leading-none text-primary">
                                {(today?.concepts_studied ?? 0).toLocaleString()}
                            </span>
                            <span className="text-[9px] uppercase tracking-widest text-muted-foreground">Studied Today</span>
                        </div>
                    </div>
                </m.div>
            </div>
        </div>
    )
}
