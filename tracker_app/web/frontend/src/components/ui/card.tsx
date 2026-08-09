import * as React from 'react'
import { cn } from '@/lib/utils'

function Card({ className, ...props }: React.ComponentProps<'div'>) {
    return (
        <div
            className={cn('border border-border bg-card text-card-foreground', className)}
            {...props}
        />
    )
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
    return <div className={cn('flex flex-col gap-1 p-4', className)} {...props} />
}

function CardTitle({ className, ...props }: React.ComponentProps<'h3'>) {
    return (
        <h3
            className={cn('text-[10px] font-mono uppercase tracking-[0.12em] text-muted-foreground', className)}
            {...props}
        />
    )
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
    return <div className={cn('p-4 pt-0', className)} {...props} />
}

function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
    return <div className={cn('flex items-center p-4 pt-0', className)} {...props} />
}

export { Card, CardHeader, CardTitle, CardContent, CardFooter }
