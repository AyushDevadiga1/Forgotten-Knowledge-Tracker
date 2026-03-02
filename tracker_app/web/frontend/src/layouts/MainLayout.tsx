import { NavLink, Outlet } from 'react-router-dom'
import { Home, Activity, Database, PlusCircle, Search } from 'lucide-react'

const navItems = [
    { id: '', icon: Home, label: 'Overview' },
    { id: 'review', icon: Activity, label: 'Review Session' },
    { id: 'database', icon: Database, label: 'Knowledge Base' },
    { id: 'add', icon: PlusCircle, label: 'Add Concept' },
]

export default function MainLayout() {
    return (
        <div className="min-h-screen bg-fkt-base text-fkt-text-muted font-sans flex overflow-hidden">
            <svg className="hidden">
                <defs>
                    <linearGradient id="accentGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00FFA3" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#00FFA3" stopOpacity={0} />
                    </linearGradient>
                </defs>
            </svg>

            {/* Collapsible Sidebar */}
            <aside className="fixed left-0 top-0 h-full w-[48px] hover:w-[200px] transition-all duration-200 ease-in-out bg-fkt-surface border-r border-fkt-elevated z-50 overflow-hidden group flex flex-col py-4">
                <div className="px-3 h-[32px] flex items-center mb-6 shrink-0">
                    <span className="font-mono text-fkt-accent text-xs font-bold whitespace-nowrap overflow-hidden">
                        FKT
                    </span>
                </div>
                <nav className="w-full space-y-1 flex flex-col px-2">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.id}
                            to={`/${item.id}`}
                            end={item.id === ''}
                            className={({ isActive }) =>
                                `flex items-center w-full px-2 py-2.5 transition-colors duration-150 ${isActive
                                    ? 'text-fkt-accent bg-fkt-elevated'
                                    : 'text-fkt-text-muted hover:bg-fkt-elevated hover:text-fkt-text-primary'
                                }`
                            }
                        >
                            <item.icon className="min-w-[20px]" size={18} strokeWidth={1.5} />
                            <span className="ml-4 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 delay-100 uppercase tracking-[0.12em] text-[10px] font-semibold">
                                {item.label}
                            </span>
                        </NavLink>
                    ))}
                </nav>
            </aside>

            {/* Main Content */}
            <main className="ml-[48px] flex-1 flex flex-col h-screen overflow-y-auto w-full">
                {/* Top Header */}
                <header className="sticky top-0 h-[48px] bg-fkt-base/90 backdrop-blur-sm border-b border-fkt-elevated z-40 flex items-center justify-between px-6 shrink-0">
                    <span className="text-fkt-text-primary font-mono text-xs uppercase tracking-widest">
                        SYS_MONITOR <span className="text-fkt-text-dim">// FKT v1.0</span>
                    </span>
                    <div className="flex items-center gap-4 text-fkt-text-muted">
                        <Search size={14} strokeWidth={1.5} />
                        <span className="text-[11px] font-mono">CMD+K</span>
                        <div className="w-1.5 h-1.5 bg-fkt-accent" title="System Online" />
                    </div>
                </header>

                {/* Routed Page Content */}
                <div className="p-5 flex-1">
                    <Outlet />
                </div>
            </main>
        </div>
    )
}
