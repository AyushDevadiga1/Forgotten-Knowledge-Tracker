import React from 'react';
import { Play } from 'lucide-react';

export default function ReviewPage() {
    return (
        <div className="h-full w-full flex flex-col items-center justify-center relative">
            <div className="w-full max-w-2xl">
                <div className="flex justify-between items-center mb-6 text-fkt-text-muted">
                    <span className="text-[10px] uppercase tracking-[0.12em]">REVIEW SESSION // 1 OF 24</span>
                    <span className="font-mono text-fkt-accent text-xs">4.2% DUE</span>
                </div>

                {/* Flashcard container */}
                <div className="bg-fkt-surface border border-fkt-elevated p-12 min-h-[300px] flex flex-col justify-center items-center text-center group relative [clip-path:polygon(0_0,calc(100%-16px)_0,100%_16px,100%_100%,0_100%)]">
                    <div className="absolute top-0 left-0 w-full h-full border border-transparent group-hover:border-fkt-accent/30 transition-all pointer-events-none z-10" />

                    <h2 className="text-2xl text-fkt-text-primary font-sans mb-8">What is an AVL Tree?</h2>

                    {/* Answer State (Hidden by default in flow, rendered here for demo) */}
                    <p className="text-fkt-text-muted max-w-lg mb-12">
                        A self-balancing binary search tree where the height of the two child subtrees of any node differ by at most one. Lookup, insertion, and deletion all take O(log n) time.
                    </p>

                    {/* Rating Scale */}
                    <div className="flex space-x-[1px] w-full max-w-md bg-fkt-elevated p-[1px] mt-auto">
                        {['AGAIN', 'HARD', 'GOOD', 'EASY'].map((label, idx) => (
                            <button
                                key={label}
                                className="flex-1 bg-fkt-surface py-3 text-[10px] font-mono text-fkt-text-muted hover:text-fkt-accent hover:bg-fkt-base transition-colors"
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
