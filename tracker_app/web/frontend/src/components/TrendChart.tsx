import { useState, useId } from 'react'
import { m, useReducedMotion } from 'motion/react'
import { easeOut } from '@/lib/animation'

interface TrendChartProps {
    /** Real per-day series, e.g. [{ v: 12 }, { v: 18 }, ...]. */
    data: { v: number }[]
    color?: string
    height?: number
    className?: string
}

/** Lightweight SVG area/line chart (Bklit-style, no recharts) driven by the
 * real /stats/trend series. The line path draws itself on mount. */
export default function TrendChart({ data, color = 'var(--primary)', height = 32, className }: TrendChartProps) {
    const reduced = useReducedMotion()
    const gradientId = useId().replace(/[:]/g, '')
    const [hoverIdx, setHoverIdx] = useState<number | null>(null)
    if (data.length < 2) return null

    const W = 300
    const H = height
    const max = Math.max(...data.map((d) => d.v), 1)
    const step = W / (data.length - 1)
    const pts = data.map((d, i) => ({ x: i * step, y: H - (d.v / max) * (H - 4) - 2 }))
    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')
    const area = `${line} L${W},${H} L0,${H} Z`

    const onMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
        const rect = e.currentTarget.getBoundingClientRect()
        const x = ((e.clientX - rect.left) / rect.width) * W
        const idx = Math.round(x / step)
        setHoverIdx(Math.max(0, Math.min(data.length - 1, idx)))
    }

    return (
        <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            className={className}
            style={{ width: '100%', height, cursor: 'crosshair' }}
            aria-hidden="true"
            onMouseMove={onMouseMove}
            onMouseLeave={() => setHoverIdx(null)}
        >
            <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                    <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
            </defs>
            <m.path
                d={area}
                fill={`url(#${gradientId})`}
                initial={reduced ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4, ease: easeOut }}
            />
            <m.path
                d={line}
                fill="none"
                stroke={color}
                strokeWidth={1.5}
                strokeLinecap="square"
                initial={reduced ? false : { pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.8, ease: easeOut }}
            />
            {hoverIdx !== null && (
                <>
                    <line
                        x1={pts[hoverIdx].x}
                        y1={0}
                        x2={pts[hoverIdx].x}
                        y2={H}
                        stroke={color}
                        strokeWidth={0.5}
                        strokeOpacity={0.4}
                    />
                    <circle cx={pts[hoverIdx].x} cy={pts[hoverIdx].y} r={2} fill={color} />
                    <text
                        x={pts[hoverIdx].x}
                        y={Math.max(10, pts[hoverIdx].y - 6)}
                        textAnchor="middle"
                        fill={color}
                        fontSize={10}
                        fontFamily="monospace"
                    >
                        {data[hoverIdx].v}
                    </text>
                </>
            )}
        </svg>
    )
}
