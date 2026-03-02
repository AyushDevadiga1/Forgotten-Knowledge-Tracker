export default function AddConceptPage() {
    return (
        <div className="flex flex-col items-center justify-center h-full">
            <div className="w-full max-w-xl bg-fkt-surface border border-fkt-elevated p-8 hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]">
                <h2 className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-8 font-mono">MANUAL INGESTION — ADD CONCEPT</h2>

                <form className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-[10px] font-mono text-fkt-text-muted block">QUESTION / TOPIC</label>
                        <input
                            className="w-full bg-fkt-base border border-fkt-elevated p-3 text-sm text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors placeholder:text-fkt-text-dim"
                            placeholder="e.g. What is the Big-O complexity of quicksort?"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-mono text-fkt-text-muted block">ANSWER / EXPLANATION</label>
                        <textarea
                            className="w-full h-28 bg-fkt-base border border-fkt-elevated p-3 text-sm text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors resize-none placeholder:text-fkt-text-dim"
                            placeholder="e.g. Average O(n log n), worst case O(n²)."
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-mono text-fkt-text-muted block">DIFFICULTY</label>
                            <select className="w-full bg-fkt-base border border-fkt-elevated p-3 text-[12px] font-mono text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors">
                                <option>EASY</option>
                                <option>MEDIUM</option>
                                <option>HARD</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-mono text-fkt-text-muted block">TYPE</label>
                            <select className="w-full bg-fkt-base border border-fkt-elevated p-3 text-[12px] font-mono text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors">
                                <option>CONCEPT</option>
                                <option>DEFINITION</option>
                                <option>CODE</option>
                            </select>
                        </div>
                    </div>

                    <button
                        type="button"
                        className="w-full mt-2 py-4 border border-fkt-accent bg-fkt-accent/10 text-fkt-accent text-[12px] font-mono uppercase hover:bg-fkt-accent/20 transition-colors"
                    >
                        INGEST ITEM
                    </button>
                </form>
            </div>
        </div>
    )
}
