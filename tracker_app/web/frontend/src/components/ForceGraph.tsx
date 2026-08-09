import { useEffect, useMemo, useRef, useState } from 'react'
import { createTimeline, stagger } from 'animejs'
import { useReducedMotion } from 'motion/react'
import type { GraphNode, GraphEdge } from '@/api'

const W = 820
const H = 440
const PAD = 44

interface Point { x: number; y: number }

function simulateLayout(nodes: GraphNode[], links: GraphEdge[]): Point[] {
    const n = nodes.length
    const pos: (Point & { vx: number; vy: number })[] = nodes.map(() => ({
        x: W / 2 + (Math.random() - 0.5) * W * 0.25,
        y: H / 2 + (Math.random() - 0.5) * H * 0.25,
        vx: 0,
        vy: 0,
    }))
    const index = new Map(nodes.map((node, i) => [node.concept, i]))
    const k = Math.sqrt((W * H) / Math.max(n, 1)) * 0.6

    for (let iter = 0; iter < 220; iter++) {
        const temp = Math.max(0.01, 1 - iter / 220)
        // repulsion (all pairs)
        for (let i = 0; i < n; i++) {
            for (let j = i + 1; j < n; j++) {
                const dx = pos[i].x - pos[j].x
                const dy = pos[i].y - pos[j].y
                const dist = Math.max(Math.hypot(dx, dy), 0.1)
                const f = ((k * k) / (dist * dist)) * temp
                const fx = (dx / dist) * f
                const fy = (dy / dist) * f
                pos[i].vx += fx
                pos[i].vy += fy
                pos[j].vx -= fx
                pos[j].vy -= fy
            }
        }
        // attraction along weighted edges
        for (const link of links) {
            const i = index.get(link[0])
            const j = index.get(link[1])
            if (i === undefined || j === undefined) continue
            const dx = pos[j].x - pos[i].x
            const dy = pos[j].y - pos[i].y
            const dist = Math.max(Math.hypot(dx, dy), 0.1)
            const f = ((dist * dist) / k) * link[2] * temp * 0.55
            const fx = (dx / dist) * f
            const fy = (dy / dist) * f
            pos[i].vx += fx
            pos[i].vy += fy
            pos[j].vx -= fx
            pos[j].vy -= fy
        }
        for (let i = 0; i < n; i++) {
            pos[i].x += pos[i].vx * temp
            pos[i].y += pos[i].vy * temp
            pos[i].x += (W / 2 - pos[i].x) * 0.012
            pos[i].y += (H / 2 - pos[i].y) * 0.012
            pos[i].vx *= 0.94
            pos[i].vy *= 0.94
        }
    }
    return pos.map((p) => ({
        x: Math.min(W - PAD, Math.max(PAD, p.x)),
        y: Math.min(H - PAD, Math.max(PAD, p.y)),
    }))
}

function nodeColor(score: number): string {
    if (score >= 0.65) return '#00FFA3'
    if (score >= 0.4) return '#F59E0B'
    return '#EF4444'
}

interface ForceGraphProps {
    nodes: GraphNode[]
    links: GraphEdge[]
    onSelect: (node: GraphNode) => void
}

/** Force-directed knowledge graph. The physics layout is simulated in JS and
 * the settling-in (staggered spring to final positions) is driven by anime.js
 * — the one place this app uses it. Links draw themselves once nodes land. */
export default function ForceGraph({ nodes, links, onSelect }: ForceGraphProps) {
    const reduced = useReducedMotion()
    const [hovered, setHovered] = useState<string | null>(null)
    const [entered, setEntered] = useState(false)
    const nodeRefs = useRef<(SVGGElement | null)[]>([])
    const lineRefs = useRef<(SVGLineElement | null)[]>([])

    const final = useMemo(() => simulateLayout(nodes, links), [nodes, links])
    const center: Point = { x: W / 2, y: H / 2 }
    const starts = useMemo(
        () =>
            nodes.map((_, i) => ({
                x: center.x + (i - nodes.length / 2) * 6,
                y: center.y + ((i * 7) % 5 - 2) * 6,
            })),
        [nodes.length]
    )

    useEffect(() => {
        if (reduced) {
            setEntered(true)
            return
        }
        const gEls = nodeRefs.current.filter(Boolean) as SVGGElement[]
        if (gEls.length === 0) return
        const tl = createTimeline({ defaults: { ease: 'outExpo', duration: 950 } })
        tl.onComplete = () => setEntered(true)
        tl.add(gEls, {
            x: (_el: unknown, i?: number) => final[i ?? 0].x,
            y: (_el: unknown, i?: number) => final[i ?? 0].y,
            delay: stagger(38),
        })
        return () => { tl.cancel() }
    }, [reduced, final, nodes.length])

    // neighbour lookup for hover-highlight
    const neighbors = useMemo(() => {
        const map = new Map<string, Set<string>>()
        for (const [a, b] of links) {
            if (!map.has(a)) map.set(a, new Set())
            if (!map.has(b)) map.set(b, new Set())
            map.get(a)!.add(b)
            map.get(b)!.add(a)
        }
        return map
    }, [links])

    const linkOpacity = (l: GraphEdge): number => {
        if (!hovered) return 0.35 + l[2] * 0.5
        return hovered === l[0] || hovered === l[1] ? 0.95 : 0.06
    }

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img" aria-label="Knowledge graph">
            <g style={{ opacity: entered ? 1 : 0.35, transition: 'opacity 0.6s ease' }}>
                {links.map((l, i) => {
                    const a = nodes.findIndex((n) => n.concept === l[0])
                    const b = nodes.findIndex((n) => n.concept === l[1])
                    if (a < 0 || b < 0) return null
                    return (
                        <line
                            key={i}
                            ref={(el) => { lineRefs.current[i] = el }}
                            x1={final[a].x}
                            y1={final[a].y}
                            x2={final[b].x}
                            y2={final[b].y}
                            stroke="#00FFA3"
                            strokeWidth={0.6 + l[2] * 2.2}
                            strokeOpacity={linkOpacity(l)}
                            style={{
                                transition: 'stroke-opacity 0.25s ease',
                                strokeDasharray: 128,
                                strokeDashoffset: entered ? 0 : 128,
                            }}
                        />
                    )
                })}
            </g>

            {nodes.map((node, i) => {
                const isDimmed =
                    hovered !== null &&
                    hovered !== node.concept &&
                    !(neighbors.get(hovered)?.has(node.concept))
                const r = 4 + node.memory_score * 9
                const color = nodeColor(node.memory_score)
                return (
                    <g
                        key={node.concept}
                        ref={(el) => { nodeRefs.current[i] = el }}
                        transform={`translate(${reduced ? final[i].x : starts[i].x} ${reduced ? final[i].y : starts[i].y})`}
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHovered(node.concept)}
                        onMouseLeave={() => setHovered(null)}
                        onClick={() => onSelect(node)}
                    >
                        <circle
                            r={r}
                            fill={color}
                            fillOpacity={isDimmed ? 0.06 : 0.15 + node.memory_score * 0.55}
                            stroke={color}
                            strokeWidth={1.2}
                            opacity={isDimmed ? 0.25 : 1}
                            style={{ transition: 'opacity 0.25s ease' }}
                        />
                        <circle
                            r={2.5}
                            fill={isDimmed ? '#334155' : color}
                            opacity={isDimmed ? 0.4 : 1}
                            style={{ transition: 'opacity 0.25s ease' }}
                        />
                        <text
                            y={-r - 5}
                            textAnchor="middle"
                            fontSize={9}
                            fontFamily="IBM Plex Mono, monospace"
                            fill="#94A3B8"
                            opacity={isDimmed ? 0.25 : hovered === node.concept ? 1 : 0.75}
                            style={{ transition: 'opacity 0.25s ease', pointerEvents: 'none' }}
                            className="select-none"
                        >
                            {node.concept.length > 16 ? node.concept.slice(0, 15) + '…' : node.concept}
                        </text>
                    </g>
                )
            })}
        </svg>
    )
}
