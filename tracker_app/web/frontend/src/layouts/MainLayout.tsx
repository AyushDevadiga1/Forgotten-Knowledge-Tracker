import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Home, Activity, Database, Settings, PlusCircle, Search } from 'lucide-react';

export default function MainLayout() {
    const navItems = [
        { id: '', icon: Home, label: 'Overview' },
        { id: 'review', icon: Activity, label: 'Review Session' },
        { id: 'database', icon: Database, label: 'Knowledge Base' },
        { id: 'add', icon: PlusCircle, label: 'Add Concept' }
    ];

    return (
        <div className="min-h-screen bg-fkt-base text-fkt-text-muted font-sans flex overflow-hidden">
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
            <aside className="fixed left-0 top-0 h-full w-[48px] hover:w-[200px] transition-all duration-200 ease-in-out bg-fkt-surface/80 backdrop-blur-[10px] border-r border-fkt-elevated z-50 overflow-hidden group flex flex-col items-start py-4">
                <nav className="w-full space-y-2 mt-12 flex flex-col px-2">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.id}
                            to={\`/\${item.id}\`}
                    className={({ isActive }) =>
                    \`flex items-center w-full px-2 py-2 transition-colors duration-150 \${
                        isActive
                            ? 'text-fkt-accent bg-fkt-elevated'
                            : 'text-fkt-text-muted hover:bg-fkt-elevated hover:text-fkt-text-primary'
                    }\`
              }
            >
                    <item.icon className="min-w-[20px]" size={20} strokeWidth={1.5} />
                    <span className="ml-4 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 delay-75 uppercase tracking-[0.12em] text-[10px] font-semibold">
                        {item.label}
                    </span>
                </NavLink>
          ))}
            </nav>
        </aside>

      {/* Main Content Area */ }
    <main className="ml-[48px] flex-1 flex flex-col h-screen overflow-y-auto w-full">
        {/* Header */}
        <header className="sticky top-0 h-[48px] bg-fkt-base/80 backdrop-blur-[10px] border-b border-fkt-elevated z-40 flex items-center justify-between px-6 shrink-0">
            <div className="flex items-center space-x-2 before:content-[''] before:absolute before:bottom-0 before:left-6 before:w-[60px] before:h-[1px] before:bg-fkt-accent">
                <span className="text-fkt-text-primary font-mono text-sm uppercase tracking-widest">
                    SYS_MONITOR // FKT
                </span>
            </div>
            <div className="flex items-center space-x-6">
                <div className="flex items-center text-fkt-text-muted">
                    <Search size={16} strokeWidth={1.5} className="mr-2" />
                    <span className="text-[12px] font-mono uppercase">CMD + K</span>
                </div>
            </div>
        </header>

        {/* Page Content Injection */}
        <div className="p-6 h-full">
            <Outlet />
        </div>
    </main>
    </div >
  );
}
