export default function ReviewPage() {
    const ratings = ['AGAIN', 'HARD', 'GOOD', 'EASY']

    return (
        <div className="h-full w-full flex flex-col items-center justify-center">
            <div className="w-full max-w-2xl">
                <div className="flex justify-between items-center mb-6 text-fkt-text-muted">
                    <span className="text-[10px] uppercase tracking-[0.12em]">REVIEW SESSION // 1 OF 24</span>
                    <span className="font-mono text-fkt-accent text-xs">4.2% DUE</span>
                </div>

                <div className="bg-fkt-surface border border-fkt-elevated p-12 min-h-[320px] flex flex-col justify-between hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow [clip-path:polygon(0_0,calc(100%-16px)_0,100%_16px,100%_100%,0_100%)]">
                    <h2 className="text-2xl text-fkt-text-primary font-sans text-center mb-6">What is an AVL Tree?</h2>
                    <p className="text-fkt-text-muted text-sm text-center max-w-md mx-auto">
                        A self-balancing binary search tree where the height of two child subtrees differ by at most one. Lookup, insert, and delete all take O(log n) time.
                    </p>

                    <div className="flex gap-[1px] mt-8">
                        {ratings.map((label) => (
                            <button
                                key={label}
                                className="flex-1 bg-fkt-base border border-fkt-elevated py-3 text-[10px] font-mono text-fkt-text-muted hover:text-fkt-accent hover:border-fkt-accent transition-colors"
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
