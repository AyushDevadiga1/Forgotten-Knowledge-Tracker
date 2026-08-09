import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
    'inline-flex items-center gap-1 rounded-none border px-2 py-0.5 text-[9px] font-mono uppercase tracking-widest transition-colors',
    {
        variants: {
            variant: {
                default: 'border-primary/30 bg-primary/10 text-primary',
                secondary: 'border-border bg-secondary text-secondary-foreground',
                destructive: 'border-destructive/40 bg-destructive/10 text-destructive',
                outline: 'border-border text-foreground',
                warning: 'border-amber-500/40 bg-amber-500/10 text-amber-500',
            },
        },
        defaultVariants: {
            variant: 'default',
        },
    }
)

function Badge({
    className,
    variant,
    ...props
}: React.ComponentProps<'span'> & VariantProps<typeof badgeVariants>) {
    return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
