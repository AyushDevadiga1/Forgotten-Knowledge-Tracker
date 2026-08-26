import { useEffect, useState, useCallback } from 'react'
import { m } from 'motion/react'
import { BarChart3, Activity, Brain, Mic, Monitor } from 'lucide-react'
import { api, TelemetrySummary } from '../api'
import PageHeader from '../components/PageHeader'
import TrendChart from '../components/TrendChart'
import EmptyState from '../components/EmptyState'
import BackendDown from '../components/BackendDown'
import { easeOut } from '../lib/animation'

function BarRow({ label, count, max }: { label: string; count: number; max: number }) {
    const pct = max > 0 ? (count / max) * 100 : 0
    return (
        <div className="flex items-center gap-2">
            <span className="w-[120px] truncate font-mono text-[10px] text-muted-foreground">{label}</span>
            <div className="h-2 flex-1 bg-border">
                <m.div
                    className="h-full bg-primary"
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.4, ease: easeOut }}
                />
            </div>
            <span className="w-[32px] text-right font-mono text-[10px] text-muted-foreground">{count}</span>
        </div>
    )
}

function PanelTitle({ icon: Icon, children }: { icon: React.ElementType; children: React.ReactNode }) {
    return (
        <span className="mb-3 flex items-center gap-1.5 text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
            <Icon size={11} strokeWidth={1.5} />
            {children}
        </span>
    )
}

export default function TelemetryPage() {
    const [data, setData] = useState<TelemetrySummary | null>(null)
    const [loading, setLoading] = useState(true)
    const [backendDown, setBackendDown] = useState(false)

    const fetchData = useCallback(async () => {
        try {
            const res = await api.getTelemetrySummary()
            setData(res.data)
            setBackendDown(false)
        } catch {
            setBackendDown(true)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchData() }, [fetchData])

    if (loading) {
        return (
            <div className="flex h-64 items-center justify-center">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    Loading telemetry...
                </span>
            </div>
        )
    }
    if (backendDown) return <BackendDown />
    if (!data || data.total_logs === 0) {
        return (
            <EmptyState
                label="No telemetry data yet"
                hint="Start a study session with the tracker running to collect attention, intent, and activity data."
            />
        )
    }

    const maxKeyword = Math.max(...data.top_keywords.map(k => k.count), 1)
    const maxWindow = Math.max(...data.top_windows.map(w => w.count), 1)
    const maxIntent = Math.max(...data.intent_distribution.map(i => i.count), 1)

    return (
        <div className="mx-auto max-w-3xl space-y-5">
            <PageHeader
                icon={BarChart3}
                title="Telemetry"
                subtitle={`Session data from the last 24 hours (${data.total_logs} log entries)`}
            />

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="col-span-full border border-border bg-card p-4">
                    <PanelTitle icon={Activity}>Attention Over Time</PanelTitle>
                    {data.attention_series.length > 1 ? (
                        <TrendChart
                            data={data.attention_series.map(s => ({ v: s.v }))}
                            color="var(--primary)"
                            height={80}
                        />
                    ) : (
                        <p className="font-mono text-[10px] text-muted-foreground">Not enough data points for a chart</p>
                    )}
                </div>

                <div className="border border-border bg-card p-4">
                    <PanelTitle icon={Brain}>Intent Distribution</PanelTitle>
                    <div className="space-y-1.5">
                        {data.intent_distribution.map(item => (
                            <BarRow key={item.label} label={item.label} count={item.count} max={maxIntent} />
                        ))}
                    </div>
                </div>

                <div className="border border-border bg-card p-4">
                    <PanelTitle icon={Mic}>Audio Labels</PanelTitle>
                    <div className="space-y-1.5">
                        {data.audio_distribution.map(item => (
                            <BarRow key={item.label} label={item.label} count={item.count} max={maxKeyword} />
                        ))}
                    </div>
                </div>

                <div className="border border-border bg-card p-4">
                    <PanelTitle icon={BarChart3}>Top OCR Keywords</PanelTitle>
                    <div className="space-y-1.5">
                        {data.top_keywords.map(item => (
                            <BarRow key={item.keyword} label={item.keyword} count={item.count} max={maxKeyword} />
                        ))}
                    </div>
                </div>

                <div className="border border-border bg-card p-4">
                    <PanelTitle icon={Monitor}>Window Time</PanelTitle>
                    <div className="space-y-1.5">
                        {data.top_windows.map(item => (
                            <BarRow key={item.window} label={item.window} count={item.count} max={maxWindow} />
                        ))}
                    </div>
                </div>

                {data.intent_accuracy.length > 0 && (
                    <div className="col-span-full border border-border bg-card p-4">
                        <PanelTitle icon={Brain}>Intent Accuracy</PanelTitle>
                        <div className="flex flex-wrap gap-3">
                            {data.intent_accuracy.map(item => (
                                <div
                                    key={item.intent}
                                    className="border border-border bg-background px-3 py-2"
                                >
                                    <span className="block font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                                        {item.intent}
                                    </span>
                                    <span className="font-mono text-lg text-foreground">
                                        {item.accuracy}%
                                    </span>
                                    <span className="ml-1 font-mono text-[9px] text-muted-foreground">
                                        ({item.total})
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
