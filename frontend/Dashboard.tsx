import React, { useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, ResponsiveContainer, Tooltip as RechartsTooltip, Cell
} from 'recharts';
import { Home, Activity, Database, Settings, Search, Monitor, Code, BookOpen } from 'lucide-react';

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

export default function Dashboard() {
  const [activeNav, setActiveNav] = useState('home');

  return (
    <div className="min-h-screen bg-[#0D1117] text-[#94A3B8] font-['DM_Sans',sans-serif] selection:bg-[#00FFA3] selection:text-[#0D1117] flex overflow-hidden">
      
      {/* SVG Definitions for Gradients */}
      <svg className="hidden">
        <defs>
          <linearGradient id="accentGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00FFA3" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#00FFA3" stopOpacity={0} />
          </linearGradient>
        </defs>
      </svg>

      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-[48px] hover:w-[200px] transition-all duration-200 ease-in-out bg-[#0F172A]/80 backdrop-blur-[10px] border-r border-[#1E293B] z-50 overflow-hidden group flex flex-col items-start py-4">
        <nav className="w-full space-y-2 mt-12 flex flex-col px-2">
          {[
            { id: 'home', icon: Home, label: 'Overview' },
            { id: 'activity', icon: Activity, label: 'Activity' },
            { id: 'database', icon: Database, label: 'Knowledge Base' },
            { id: 'settings', icon: Settings, label: 'Settings' }
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveNav(item.id)}
              className={\`flex items-center w-full px-2 py-2 rounded-none transition-colors duration-150 \${
                activeNav === item.id 
                  ? 'text-[#00FFA3] bg-[#1E293B]' 
                  : 'text-[#475569] hover:bg-[#1E293B] hover:text-[#F1F5F9]'
              }\`}
            >
              <item.icon className="min-w-[20px]" size={20} strokeWidth={1.5} />
              <span className="ml-4 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 delay-75 uppercase tracking-[0.12em] text-[10px] font-semibold">
                {item.label}
              </span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="ml-[48px] flex-1 flex flex-col h-screen overflow-y-auto w-full">
        
        {/* Header */}
        <header className="sticky top-0 h-[48px] bg-[#0D1117]/80 backdrop-blur-[10px] border-b border-[#1E293B] z-40 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center space-x-2 before:content-[''] before:absolute before:bottom-0 before:left-6 before:w-[60px] before:h-[1px] before:bg-[#00FFA3]">
            <span className="text-[#F1F5F9] font-['IBM_Plex_Mono',monospace] text-sm uppercase tracking-widest">
              SYS_MONITOR // FKT
            </span>
          </div>
          <div className="flex items-center space-x-6">
            <div className="flex items-center text-[#64748B]">
              <Search size={16} strokeWidth={1.5} className="mr-2" />
              <span className="text-[12px] font-['IBM_Plex_Mono',monospace] uppercase">CMD + K</span>
            </div>
          </div>
        </header>

        {/* Dashboard Grid Container */}
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-[1px] bg-[#1E293B] border border-[#1E293B]">
            
            {/* 1. TOP ROW: KPI CARDS */}
            {MOCK_DATA.kpi.map((kpi, idx) => (
              <div 
                key={idx} 
                className={\`bg-[#0F172A] p-4 flex flex-col justify-between group transition-all duration-200 hover:border-[#00FFA3]/30 
                  \${idx === 0 ? '[clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)] relative' : ''}
                  \${idx === 0 || idx === 1 ? 'md:col-span-1' : 'md:col-span-1'}
                \`}
              >
                {/* 1px glowing primary accent for the first card */}
                {idx === 0 && (
                  <div className="absolute top-0 left-0 w-full h-full border border-transparent group-hover:border-[#00FFA3]/30 shadow-[0_0_0_1px_rgba(0,255,163,0)] group-hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)] transition-all pointer-events-none z-10" />
                )}

                <div className="flex justify-between items-start mb-6">
                  <span className="text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
                    {kpi.title}
                  </span>
                  <span className={\`text-[10px] font-['IBM_Plex_Mono'] px-1.5 py-0.5 \${kpi.trend === 'up' ? 'text-[#00FFA3] bg-[#00FFA3]/10' : 'text-[#64748B] bg-[#1E293B]'}\`}>
                    {kpi.delta}
                  </span>
                </div>
                
                <div className="flex items-end justify-between">
                  <span className="font-['IBM_Plex_Mono',monospace] text-[clamp(1.8rem,3vw,2.8rem)] leading-none text-[#F1F5F9]">
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
            <div className="md:col-span-2 md:row-span-2 bg-[#0F172A] p-4 flex flex-col group transition-all duration-200 hover:border-[#00FFA3]/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)]">
              <div className="flex justify-between items-center mb-6">
                <span className="text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
                  INTERACTION VOLUME // 30D
                </span>
                <div className="flex border border-[#1E293B]">
                  {['24H', '7D', '30D'].map((range, i) => (
                    <button key={range} className={\`px-3 py-1 text-[10px] font-['IBM_Plex_Mono'] \${i === 2 ? 'bg-[#1E293B] text-[#F1F5F9]' : 'text-[#64748B] hover:text-[#F1F5F9]'} transition-colors\`}>
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
            <div className="md:col-span-1 bg-[#0F172A] p-4 flex flex-col group transition-all duration-200 hover:border-[#00FFA3]/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)]">
              <div className="flex justify-between items-center mb-4">
                <span className="text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
                  RECENTLY EXTRACTED
                </span>
                <Search size={12} className="text-[#64748B]" />
              </div>
              <div className="flex flex-col flex-1 text-[12px]">
                {MOCK_DATA.recentConcepts.map((concept, i) => (
                  <div key={i} className="flex justify-between items-center py-2.5 hover:bg-[#1E293B] transition-none px-2 -mx-2 cursor-default">
                    <div className="flex items-center space-x-3">
                      <span className="font-['IBM_Plex_Mono'] text-[#475569]">{concept.id}</span>
                      <span className="text-[#F1F5F9] truncate max-w-[100px]">{concept.topic}</span>
                    </div>
                    <div className="flex items-center space-x-3 text-right">
                      <span className="font-['IBM_Plex_Mono'] text-[#00FFA3] opacity-80">{(concept.match * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
              <button className="mt-4 w-full py-2 border border-[#1E293B] bg-[#0F172A] text-[#F1F5F9] text-[11px] font-['IBM_Plex_Mono'] uppercase hover:border-[#00FFA3] hover:text-[#00FFA3] transition-colors duration-200">
                VIEW ALL LOGS
              </button>
            </div>

            {/* 4. STATUS LIST CARD */}
            <div className="md:col-span-1 bg-[#0F172A] p-4 flex flex-col group transition-all duration-200 hover:border-[#00FFA3]/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)]">
              <span className="text-[10px] uppercase tracking-[0.12em] text-[#64748B] mb-4 block">
                SYSTEM HEALTH
              </span>
              <div className="flex flex-col space-y-3">
                {MOCK_DATA.statusFeed.map((status, i) => (
                  <div key={i} className="flex justify-between items-center p-2 border border-[#1E293B] bg-[#0D1117]">
                    <div className="flex items-center space-x-2">
                      <div className={\`w-1.5 h-1.5 rounded-none \${
                        status.status === 'healthy' ? 'bg-[#00FFA3]' : 
                        status.status === 'warning' ? 'bg-[#F59E0B]' : 
                        'bg-[#EF4444]'
                      }\`} />
                      <span className="text-[#F1F5F9] text-[12px]">{status.service}</span>
                    </div>
                    <span className="font-['IBM_Plex_Mono'] text-[10px] text-[#64748B]">{status.latency}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 5. SECONDARY CHART */}
            <div className="md:col-span-2 bg-[#0F172A] p-4 flex flex-col group transition-all duration-200 hover:border-[#00FFA3]/30 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.15)] [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]">
               <span className="text-[10px] uppercase tracking-[0.12em] text-[#64748B] mb-4 block">
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
        </div>
      </main>

    </div>
  );
}
