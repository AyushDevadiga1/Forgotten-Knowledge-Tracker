import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
    'inline-flex items-center justify-center gap-2 whitespace-nowrap text-xs font-mono uppercase tracking-widest transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0',
    {
        variants: {
            variant: {
                default:
                    'bg-primary text-primary-foreground hover:bg-primary/90 shadow-fkt-glow-sm',
                destructive:
                    'bg-destructive text-destructive-foreground hover:bg-destructive/90',
                outline:
                    'border border-border bg-transparent hover:border-primary hover:text-primary',
                secondary:
                    'bg-secondary text-secondary-foreground hover:bg-secondary/80',
                ghost: 'hover:bg-muted hover:text-foreground',
                link: 'text-primary underline-offset-4 hover:underline',
            },
            size: {
                default: 'h-9 px-4 py-2',
                sm: 'h-8 px-3 text-[10px]',
                lg: 'h-10 px-6',
                icon: 'h-9 w-9',
            },
        },
        defaultVariants: {
            variant: 'default',
            size: 'default',
        },
    }
)

function Button({
    className,
    variant,
    size,
    ...props
}: React.ComponentProps<'button'> & VariantProps<typeof buttonVariants>) {
    return (
        <button
            className={cn(buttonVariants({ variant, size, className }))}
            {...props}
        />
    )
}

export { Button, buttonVariants }
