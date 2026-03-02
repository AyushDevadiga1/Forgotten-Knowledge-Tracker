import React from 'react';

export default function AddConceptPage() {
    return (
        <div className="h-full w-full flex flex-col items-center justify-center relative">
            <div className="w-full max-w-xl bg-fkt-surface border border-fkt-elevated p-8 group relative [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]">
                <div className="absolute top-0 left-0 w-full h-full border border-transparent group-hover:border-fkt-accent/30 transition-all pointer-events-none z-10" />

                <h2 className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-8">MANUAL INGESTION // ADD CONCEPT</h2>

                <form className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-[10px] font-mono text-fkt-text-muted">QUESTION / TOPIC</label>
                        <input
                            className="w-full bg-fkt-base border border-fkt-elevated p-3 text-sm text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors"
                            placeholder="e.g. What is the Big-O complexity of quicksort?"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-mono text-fkt-text-muted">ANSWER / EXPLANATION</label>
                        <textarea
                            className="w-full h-32 bg-fkt-base border border-fkt-elevated p-3 text-sm text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors resize-none"
                            placeholder="e.g. Average O(n log n), worst case O(n^2)."
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-mono text-fkt-text-muted">DIFFICULTY</label>
                            <select className="w-full bg-fkt-base border border-fkt-elevated p-3 text-[12px] font-mono text-fkt-text-primary outline-none">
                                <option>EASY</option>
                                <option>MEDIUM</option>
                                <option>HARD</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-mono text-fkt-text-muted">TYPE</label>
                            <select className="w-full bg-fkt-base border border-fkt-elevated p-3 text-[12px] font-mono text-fkt-text-primary outline-none">
                                <option>CONCEPT</option>
                                <option>DEFINITION</option>
                                <option>CODE</option>
                            </select>
                        </div>
                    </div>

                    <button
                        type="button"
                        className="w-full mt-4 py-4 border border-fkt-accent bg-fkt-accent/10 text-fkt-accent text-[12px] font-mono uppercase hover:bg-fkt-accent/20 hover:shadow-[0_0_0_1px_rgba(0,255,163,0.3)] transition-all duration-200"
                    >
                        INGEST ITEM
                    </button>
                </form>

            </div>
        </div>
    );
}
