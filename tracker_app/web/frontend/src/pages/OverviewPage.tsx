import { useEffect, useState } from 'react'
import { AreaChart, Area, BarChart, Bar, ResponsiveContainer, Tooltip as RCTooltip, Cell } from 'recharts'
import { Search, AlertCircle, Loader } from 'lucide-react'
import { api, Stats, LearningItem } from '../api'

const tooltipStyle = {
  contentStyle: { backgroundColor: '#0F172A', borderColor: '#1E293B', borderRadius: 0, fontFamily: 'IBM Plex Mono', fontSize: '12px', color: '#F1F5F9' },
  itemStyle: { color: '#00FFA3' },
}

const statusColor: Record<string, string> = {
  healthy: 'bg-fkt-accent',
  warning: 'bg-[#F59E0B]',
  critical: 'bg-[#EF4444]',
}

// Build sparkline from a single number (simulated trend)
function miniSparkline(base: number): { v: number }[] {
  return Array.from({ length: 7 }, (_, i) => ({
    v: Math.max(0, base + Math.round((Math.random() - 0.5) * base * 0.2) + i),
  }))
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [today, setToday] = useState<{ reviews_today: number; concepts_studied: number } | null>(null)
  const [recentItems, setRecentItems] = useState<LearningItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [statsRes, itemsRes] = await Promise.all([
          api.getStats(),
          api.getItems('active', 6),
        ])
        setStats(statsRes.data.stats)
        setToday(statsRes.data.today)
        setRecentItems(itemsRes.data)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-full gap-3 text-fkt-text-muted">
      <Loader size={18} strokeWidth={1.5} className="animate-spin text-fkt-accent" />
      <span className="font-mono text-xs uppercase tracking-widest">Loading live data…</span>
    </div>
  )

  if (error) return (
    <div className="flex items-center justify-center h-full gap-3 text-[#EF4444]">
      <AlertCircle size={18} strokeWidth={1.5} />
      <span className="font-mono text-xs">Backend offline — {error}</span>
    </div>
  )

  const kpi = stats ? [
    {
      title: 'TOTAL ITEMS',
      value: stats.total_items.toLocaleString(),
      delta: `${stats.active_items} active`,
      up: true,
      spark: miniSparkline(stats.total_items),
    },
    {
      title: 'MASTERED',
      value: stats.mastered_items.toLocaleString(),
      delta: `${Math.round((stats.mastered_items / Math.max(stats.total_items, 1)) * 100)}%`,
      up: true,
      spark: miniSparkline(stats.mastered_items),
    },
    {
      title: 'AVG SUCCESS',
      value: `${Math.round(stats.average_success_rate)}%`,
      delta: `${stats.total_reviews} total reviews`,
      up: stats.average_success_rate >= 70,
      spark: miniSparkline(stats.average_success_rate),
    },
    {
      title: 'DUE TODAY',
      value: stats.items_due_today.toLocaleString(),
      delta: `${today?.reviews_today ?? 0} reviewed`,
      up: stats.items_due_today === 0,
      spark: miniSparkline(stats.items_due_today + 1),
    },
  ] : []

  const distData = [
    { cat: 'Active', v: stats?.active_items ?? 0 },
    { cat: 'Mastered', v: stats?.mastered_items ?? 0 },
    { cat: 'Due', v: stats?.items_due_today ?? 0 },
    { cat: 'Reviews', v: today?.reviews_today ?? 0 },
    { cat: 'Streak', v: stats?.current_streak ?? 0 },
  ]

  return (
    <div className="grid grid-cols-4 gap-[1px] bg-fkt-elevated">

      {/* KPI CARDS */}
      {kpi.map((k, i) => (
        <div
          key={i}
          className={`bg-fkt-surface p-4 flex flex-col justify-between group hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow ${i === 0 ? '[clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]' : ''
            }`}
        >
          <div className="flex justify-between items-start mb-4">
            <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">{k.title}</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 ${k.up ? 'text-fkt-accent bg-fkt-accent/10' : 'text-[#F59E0B] bg-[#F59E0B]/10'}`}>
              {k.delta}
            </span>
          </div>
          <div className="flex items-end justify-between">
            <span className="font-mono text-3xl leading-none text-fkt-text-primary">{k.value}</span>
            <div className="w-[80px] h-[32px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={k.spark}>
                  <Area type="monotone" dataKey="v" stroke={k.up ? '#00FFA3' : '#64748B'} fill="url(#accentGradient)" strokeWidth={1.5} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ))}

      {/* MAIN CHART — distribution over time (session chart) */}
      <div className="col-span-2 row-span-2 bg-fkt-surface p-4 flex flex-col hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-4 block">PERFORMANCE OVERVIEW</span>
        <div className="flex-1 min-h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={distData} margin={{ top: 4, right: 0, left: -24, bottom: 0 }}>
              <RCTooltip {...tooltipStyle} cursor={{ fill: '#1E293B' }} />
              <Bar dataKey="v" fill="#1E293B" animationDuration={800} label={{ fill: '#64748B', fontSize: 10, position: 'top', fontFamily: 'IBM Plex Mono' }}>
                {distData.map((_, i) => (
                  <Cell key={i} fill={i === 0 ? '#00FFA3' : i === 1 ? 'rgba(0,255,163,0.4)' : '#1E293B'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* RECENT ITEMS */}
      <div className="bg-fkt-surface p-4 flex flex-col hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <div className="flex justify-between items-center mb-3">
          <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">RECENT ITEMS</span>
          <Search size={12} className="text-fkt-text-muted" />
        </div>
        <div className="flex flex-col text-[12px] flex-1 overflow-auto">
          {recentItems.length === 0 && (
            <span className="text-fkt-text-dim font-mono text-xs py-4 text-center">No items yet</span>
          )}
          {recentItems.map((item) => (
            <div key={item.id} className="flex justify-between items-center py-2.5 px-2 -mx-2 hover:bg-fkt-elevated cursor-default border-b border-fkt-elevated/30 last:border-0">
              <span className="text-fkt-text-primary truncate max-w-[140px]" title={item.question}>{item.question}</span>
              <span className={`font-mono text-[10px] px-1 ${item.success_rate >= 80 ? 'text-fkt-accent' : 'text-[#F59E0B]'}`}>
                {Math.round(item.success_rate)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* SYSTEM HEALTH */}
      <div className="bg-fkt-surface p-4 flex flex-col hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-4 block">SYSTEM STATUS</span>
        <div className="flex flex-col gap-2">
          {[
            { svc: 'Flask API', status: 'healthy', lat: ':5000' },
            { svc: 'SQLite DB', status: stats ? 'healthy' : 'critical', lat: 'local' },
            { svc: 'SM-2 Scheduler', status: (stats?.items_due_today ?? 0) > 50 ? 'warning' : 'healthy', lat: `${stats?.items_due_today ?? 0} due` },
            { svc: 'Background Tracker', status: 'warning', lat: 'check logs' },
          ].map((h, i) => (
            <div key={i} className="flex justify-between items-center p-2 border border-fkt-elevated bg-fkt-base">
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 ${statusColor[h.status]}`} />
                <span className="text-fkt-text-primary text-[12px]">{h.svc}</span>
              </div>
              <span className="font-mono text-[10px] text-fkt-text-muted">{h.lat}</span>
            </div>
          ))}
        </div>
      </div>

      {/* DISTRIBUTION */}
      <div className="col-span-2 bg-fkt-surface p-4 flex flex-col [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)] hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <div className="flex justify-between items-center mb-4">
          <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">DATA BREAKDOWN</span>
          <span className="font-mono text-[10px] text-fkt-accent">LIVE</span>
        </div>
        <div className="grid grid-cols-3 gap-[1px] bg-fkt-elevated text-center flex-1">
          {[
            { label: 'Streak', value: `${stats?.current_streak ?? 0}d` },
            { label: 'Reviews', value: (stats?.total_reviews ?? 0).toLocaleString() },
            { label: 'Studied Today', value: today?.concepts_studied ?? 0 },
          ].map(({ label, value }) => (
            <div key={label} className="bg-fkt-surface p-3 flex flex-col justify-center">
              <span className="text-fkt-text-dim text-[9px] uppercase tracking-widest mb-1">{label}</span>
              <span className="font-mono text-fkt-accent text-lg leading-none">{value}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
