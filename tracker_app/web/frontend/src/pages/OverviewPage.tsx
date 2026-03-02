import React from 'react';
import { AreaChart, Area, BarChart, Bar, ResponsiveContainer, Tooltip as RechartsTooltip, Cell } from 'recharts';
import { Search } from 'lucide-react';

const MOCK_DATA = {
    kpi: [
        { title: 'MASTERED CONCEPTS', value: '4,281', delta: '+12.5%', trend: 'up', sparkline: [10, 25, 15, 45, 30, 60, 80] },
        { title: 'ACTIVE QUEUE', value: '892', delta: '-2.4%', trend: 'down', sparkline: [80, 65, 75, 45, 50, 30, 20] },
        { title: 'TODAY ACCURACY', value: '94.2%', delta: '+1.1%', trend: 'up', sparkline: [85, 88, 86, 92, 90, 94, 94] },
        { title: 'FOCUS SESSIONS', value: '14', delta: '+4.0%', trend: 'up', sparkline: [5, 10, 8, 12, 11, 13, 14] },
    ],
    mainChart: Array.from({ length: 30 }, (_, i) => ({
        time: \`Day \${i + 1}\`,
    requests: Math.floor(Math.random() * 500) + 200 + (i * 10)
  })),
  recentConcepts: [
    { id: 'OC-192', topic: 'Red-Black Trees', match: 0.94, time: '10m ago' },
    { id: 'OC-193', topic: 'Async I/O Patterns', match: 0.88, time: '14m ago' },
    { id: 'OC-194', topic: 'OAuth 2.0 Flow', match: 0.99, time: '1h ago' },
    { id: 'OC-195', topic: 'PostgreSQL Indexes', match: 0.76, time: '2h ago' },
    { id: 'OC-196', topic: 'React Fiber', match: 0.91, time: '4h ago' },
  ],
  statusFeed: [
    { service: 'OCR Pipeline', status: 'healthy', latency: '42ms' },
    { service: 'Audio Monitor', status: 'healthy', latency: '12ms' },
    { service: 'SM-2 Scheduler', status: 'warning', latency: '980ms' },
    { service: 'Webcam Tracker', status: 'critical', latency: 'Error' },
  ],
  secondaryChart: [
    { category: 'Code', value: 85 },
    { category: 'Docs', value: 42 },
    { category: 'Video', value: 18 },
    { category: 'Idle', value: 64 },
    { category: 'Mixed', value: 31 },
  ]
};

export default function OverviewPage() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-[1px] bg-fkt-elevated border border-fkt-elevated">
      {/* 1. TOP ROW: KPI CARDS */}
      {MOCK_DATA.kpi.map((kpi, idx) => (
        <div 
          key={idx} 
          className={\`bg-fkt-surface p-4 flex flex-col justify-between group transition-all duration-200 hover:border-fkt-accent/30 
            \${idx === 0 ? '[clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)] relative' : ''}
            md:col-span-1
          \`}
        >
          {idx === 0 && (
            <div className="absolute top-0 left-0 w-full h-full border border-transparent group-hover:border-fkt-accent/30 shadow-[0_0_0_1px_rgba(0,255,163,0)] group-hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)] transition-all pointer-events-none z-10" />
          )}
          <div className="flex justify-between items-start mb-6">
            <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">
              {kpi.title}
            </span>
            <span className={\`text-[10px] font-mono px-1.5 py-0.5 \${kpi.trend === 'up' ? 'text-fkt-accent bg-fkt-accent/10' : 'text-fkt-text-muted bg-fkt-elevated'}\`}>
              {kpi.delta}
            </span>
          </div>
          <div className="flex items-end justify-between">
            <span className="font-mono text-[clamp(1.8rem,3vw,2.8rem)] leading-none text-fkt-text-primary">
              {kpi.value}
            </span>
            <div className="w-[80px] h-[32px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={kpi.sparkline.map((v, i) => ({ value: v, index: i }))}>
                  <Area 
                    type="monotone" 
                    dataKey="value" 
                    stroke={kpi.trend === 'up' ? '#00FFA3' : '#64748B'} 
                    fill={kpi.trend === 'up' ? "url(#accentGradient)" : "none"}
                    strokeWidth={1.5} 
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ))}

      {/* 2. MAIN CHART CARD */}
      <div className="md:col-span-2 md:row-span-2 bg-fkt-surface p-4 flex flex-col group transition-all duration-200 hover:border-fkt-accent/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)]">
        <div className="flex justify-between items-center mb-6">
          <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">
            INTERACTION VOLUME // 30D
          </span>
          <div className="flex border border-fkt-elevated">
            {['24H', '7D', '30D'].map((range, i) => (
              <button key={range} className={\`px-3 py-1 text-[10px] font-mono \${i === 2 ? 'bg-fkt-elevated text-fkt-text-primary' : 'text-fkt-text-muted hover:text-fkt-text-primary'} transition-colors\`}>
                {range}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 min-h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={MOCK_DATA.mainChart} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <RechartsTooltip 
                contentStyle={{ backgroundColor: '#0F172A', borderColor: '#1E293B', borderRadius: 0, fontFamily: 'IBM Plex Mono', fontSize: '12px', color: '#F1F5F9' }}
                itemStyle={{ color: '#00FFA3' }}
                cursor={{ stroke: '#1E293B', strokeWidth: 1, strokeDasharray: '4 4' }}
              />
              <Area 
                type="stepAfter" 
                dataKey="requests" 
                stroke="#00FFA3" 
                fill="url(#accentGradient)" 
                strokeWidth={1.5}
                activeDot={{ r: 4, fill: '#0D1117', stroke: '#00FFA3', strokeWidth: 1.5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. SIDE TABLE CARD (RECENT CONCEPTS) */}
      <div className="md:col-span-1 bg-fkt-surface p-4 flex flex-col group transition-all duration-200 hover:border-fkt-accent/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)]">
        <div className="flex justify-between items-center mb-4">
          <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted">
            RECENTLY EXTRACTED
          </span>
          <Search size={12} className="text-fkt-text-muted" />
        </div>
        <div className="flex flex-col flex-1 text-[12px]">
          {MOCK_DATA.recentConcepts.map((concept, i) => (
            <div key={i} className="flex justify-between items-center py-2.5 hover:bg-fkt-elevated transition-none px-2 -mx-2 cursor-default">
              <div className="flex items-center space-x-3">
                <span className="font-mono text-fkt-text-dim">{concept.id}</span>
                <span className="text-fkt-text-primary truncate max-w-[100px]">{concept.topic}</span>
              </div>
              <div className="flex items-center space-x-3 text-right">
                <span className="font-mono text-fkt-accent opacity-80">{(concept.match * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
        <button className="mt-4 w-full py-2 border border-fkt-elevated bg-fkt-surface text-fkt-text-primary text-[11px] font-mono uppercase hover:border-fkt-accent hover:text-fkt-accent transition-colors duration-200">
          VIEW ALL LOGS
        </button>
      </div>

      {/* 4. STATUS LIST CARD */}
      <div className="md:col-span-1 bg-fkt-surface p-4 flex flex-col group transition-all duration-200 hover:border-fkt-accent/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)]">
        <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-4 block">
          SYSTEM HEALTH
        </span>
        <div className="flex flex-col space-y-3">
          {MOCK_DATA.statusFeed.map((status, i) => (
            <div key={i} className="flex justify-between items-center p-2 border border-fkt-elevated bg-fkt-base">
              <div className="flex items-center space-x-2">
                <div className={\`w-1.5 h-1.5 \${
                  status.status === 'healthy' ? 'bg-fkt-accent' : 
                  status.status === 'warning' ? 'bg-[#F59E0B]' : 
                  'bg-[#EF4444]'
                }\`} />
                <span className="text-fkt-text-primary text-[12px]">{status.service}</span>
              </div>
              <span className="font-mono text-[10px] text-fkt-text-muted">{status.latency}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 5. SECONDARY CHART */}
      <div className="md:col-span-2 bg-fkt-surface p-4 flex flex-col group transition-all duration-200 hover:border-fkt-accent/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)] [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]">
          <span className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-4 block">
          ATTENTION DISTRIBUTION
        </span>
        <div className="flex-1 min-h-[120px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={MOCK_DATA.secondaryChart} layout="vertical" margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <RechartsTooltip 
                cursor={{ fill: '#1E293B', opacity: 0.5 }}
                contentStyle={{ backgroundColor: '#0F172A', borderColor: '#1E293B', borderRadius: 0, fontFamily: 'IBM Plex Mono', fontSize: '12px', color: '#F1F5F9' }}
              />
              <Bar dataKey="value" fill="#1E293B" animationDuration={1000}>
                {
                  MOCK_DATA.secondaryChart.map((entry, index) => (
                    <Cell key={\`cell-\${index}\`} className="hover:fill-[#00FFA3] transition-colors duration-200" />
                  ))
                }
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
