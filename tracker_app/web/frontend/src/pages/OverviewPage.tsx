import { AreaChart, Area, BarChart, Bar, ResponsiveContainer, Tooltip as RCTooltip, Cell } from 'recharts'
import { Search } from 'lucide-react'

const tooltipStyle = {
  contentStyle: { backgroundColor: '#0F172A', borderColor: '#1E293B', borderRadius: 0, fontFamily: 'IBM Plex Mono', fontSize: '12px', color: '#F1F5F9' },
  itemStyle: { color: '#00FFA3' },
  cursor: { stroke: '#1E293B', strokeWidth: 1, strokeDasharray: '4 4' },
}

const MOCK = {
  kpi: [
    { title: 'MASTERED CONCEPTS', value: '4,281', delta: '+12.5%', up: true, spark: [10, 25, 15, 45, 30, 60, 80] },
    { title: 'ACTIVE QUEUE', value: '892', delta: '-2.4%', up: false, spark: [80, 65, 75, 45, 50, 30, 20] },
    { title: 'TODAY ACCURACY', value: '94.2%', delta: '+1.1%', up: true, spark: [85, 88, 86, 92, 90, 94, 94] },
    { title: 'FOCUS SESSIONS', value: '14', delta: '+4.0%', up: true, spark: [5, 10, 8, 12, 11, 13, 14] },
  ],
  mainChart: Array.from({ length: 30 }, (_, i) => ({
    d: `D${i + 1}`,
    v: Math.floor(Math.random() * 400) + 200 + i * 8,
  })),
  recent: [
    { id: 'OC-192', topic: 'Red-Black Trees', pct: 94 },
    { id: 'OC-193', topic: 'Async I/O Patterns', pct: 88 },
    { id: 'OC-194', topic: 'OAuth 2.0 Flow', pct: 99 },
    { id: 'OC-195', topic: 'PostgreSQL Indexes', pct: 76 },
    { id: 'OC-196', topic: 'React Fiber', pct: 91 },
  ],
  health: [
    { svc: 'OCR Pipeline', status: 'healthy', lat: '42ms' },
    { svc: 'Audio Monitor', status: 'healthy', lat: '12ms' },
    { svc: 'SM-2 Scheduler', status: 'warning', lat: '980ms' },
    { svc: 'Webcam Tracker', status: 'critical', lat: 'Error' },
  ],
  dist: [
    { cat: 'Code', v: 85 },
    { cat: 'Docs', v: 42 },
    { cat: 'Video', v: 18 },
    { cat: 'Idle', v: 64 },
    { cat: 'Mixed', v: 31 },
  ],
}

const statusColor: Record<string, string> = {
  healthy: 'bg-fkt-accent',
  warning: 'bg-[#F59E0B]',
  critical: 'bg-[#EF4444]',
}

export default function OverviewPage() {
  return (
    <div className="grid grid-cols-4 gap-[1px] bg-fkt-elevated">

      {/* ── KPI CARDS ── */}
      {MOCK.kpi.map((k, i) => (
        <div
          key={i}
          className={`bg-fkt-surface p-4 flex flex-col justify-between group hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow ${i === 0 ? '[clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]' : ''
            }`}
        >
          <div className="flex justify-between items-start mb-4">
            <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">{k.title}</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 ${k.up ? 'text-fkt-accent bg-fkt-accent/10' : 'text-fkt-text-muted bg-fkt-elevated'}`}>
              {k.delta}
            </span>
          </div>
          <div className="flex items-end justify-between">
            <span className="font-mono text-3xl leading-none text-fkt-text-primary">{k.value}</span>
            <div className="w-[80px] h-[32px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={k.spark.map((v, j) => ({ j, v }))}>
                  <Area type="monotone" dataKey="v" stroke={k.up ? '#00FFA3' : '#64748B'} fill="url(#accentGradient)" strokeWidth={1.5} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ))}

      {/* ── MAIN CHART (2×2) ── */}
      <div className="col-span-2 row-span-2 bg-fkt-surface p-4 flex flex-col hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <div className="flex justify-between items-center mb-4">
          <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">INTERACTION VOLUME // 30D</span>
          <div className="flex border border-fkt-elevated">
            {['24H', '7D', '30D'].map((r, i) => (
              <button key={r} className={`px-3 py-1 text-[10px] font-mono ${i === 2 ? 'bg-fkt-elevated text-fkt-text-primary' : 'text-fkt-text-muted hover:text-fkt-text-primary'}`}>{r}</button>
            ))}
          </div>
        </div>
        <div className="flex-1 min-h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={MOCK.mainChart} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <RCTooltip {...tooltipStyle} />
              <Area type="stepAfter" dataKey="v" stroke="#00FFA3" fill="url(#accentGradient)" strokeWidth={1.5} activeDot={{ r: 3, fill: '#0D1117', stroke: '#00FFA3', strokeWidth: 1.5 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── RECENT CONCEPTS ── */}
      <div className="bg-fkt-surface p-4 flex flex-col hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <div className="flex justify-between items-center mb-3">
          <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">RECENTLY EXTRACTED</span>
          <Search size={12} className="text-fkt-text-muted" />
        </div>
        <div className="flex flex-col text-[12px] flex-1">
          {MOCK.recent.map((c, i) => (
            <div key={i} className="flex justify-between items-center py-2.5 px-2 -mx-2 hover:bg-fkt-elevated cursor-default">
              <div className="flex items-center gap-3">
                <span className="font-mono text-fkt-text-dim">{c.id}</span>
                <span className="text-fkt-text-primary truncate max-w-[90px]">{c.topic}</span>
              </div>
              <span className="font-mono text-fkt-accent">{c.pct}%</span>
            </div>
          ))}
        </div>
        <button className="mt-4 w-full py-2 border border-fkt-elevated text-fkt-text-muted text-[11px] font-mono uppercase hover:border-fkt-accent hover:text-fkt-accent transition-colors">
          VIEW ALL LOGS
        </button>
      </div>

      {/* ── SYSTEM HEALTH ── */}
      <div className="bg-fkt-surface p-4 flex flex-col hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-4 block">SYSTEM HEALTH</span>
        <div className="flex flex-col gap-2">
          {MOCK.health.map((h, i) => (
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

      {/* ── ATTENTION DISTRIBUTION ── */}
      <div className="col-span-2 bg-fkt-surface p-4 flex flex-col [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)] hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow">
        <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-4 block">ATTENTION DISTRIBUTION</span>
        <div className="flex-1 min-h-[120px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={MOCK.dist} layout="vertical" margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <RCTooltip cursor={{ fill: '#1E293B' }} contentStyle={tooltipStyle.contentStyle} />
              <Bar dataKey="v" fill="#1E293B" animationDuration={800}>
                {MOCK.dist.map((_, i) => <Cell key={i} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  )
}
