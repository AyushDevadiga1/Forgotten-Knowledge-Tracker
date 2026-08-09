import { type ReactNode } from 'react'
import { m } from 'motion/react'
import { type LucideIcon } from 'lucide-react'
import { easeOut } from '@/lib/animation'

interface PageHeaderProps {
    icon?: LucideIcon
    title: string
    subtitle?: string
    children?: ReactNode
}

export default function PageHeader({ icon: Icon, title, subtitle, children }: PageHeaderProps) {
    return (
        <div className="flex items-center justify-between">
            <m.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, ease: easeOut }}
            >
                <h1 className="flex items-center gap-2 font-mono text-sm uppercase tracking-widest text-foreground">
                    {Icon && <Icon size={14} className="text-primary" />}
                    {title}
                </h1>
                {subtitle && <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{subtitle}</p>}
            </m.div>
            {children}
        </div>
    )
}
