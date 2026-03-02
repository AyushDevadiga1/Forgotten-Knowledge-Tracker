import React from 'react';
import { Search } from 'lucide-react';

const KNOWLEDGE_ITEMS = [
    { id: 'OC-192', topic: 'Red-Black Trees', type: 'CONCEPT', success: 94, reviews: 14 },
    { id: 'OC-193', topic: 'Async I/O Patterns', type: 'IMPLEMENTATION', success: 88, reviews: 31 },
    { id: 'OC-194', topic: 'OAuth 2.0 Flow', type: 'PROTOCOL', success: 99, reviews: 8 },
    { id: 'OC-195', topic: 'PostgreSQL Indexes', type: 'DATABASE', success: 76, reviews: 42 },
];

export default function KnowledgeBasePage() {
    return (
        <div className="h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-xl text-fkt-text-primary font-sans">KNOWLEDGE BASE</h1>
                <div className="flex items-center border border-fkt-elevated bg-fkt-surface px-3 py-1.5 w-64">
                    <Search size={14} className="text-fkt-text-muted mr-2" />
                    <input
                        type="text"
                        placeholder="Search concepts..."
                        className="bg-transparent border-none outline-none text-[12px] font-mono text-fkt-text-primary w-full"
                    />
                </div>
            </div>

            <div className="flex-1 bg-fkt-surface border border-fkt-elevated">
                <table className="w-full text-left">
                    <thead className="bg-fkt-base border-b border-fkt-elevated">
                        <tr>
                            <th className="p-4 text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted font-normal">ID</th>
                            <th className="p-4 text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted font-normal">Topic</th>
                            <th className="p-4 text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted font-normal">Category</th>
                            <th className="p-4 text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted font-normal">Success</th>
                            <th className="p-4 text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted font-normal">Reviews</th>
                        </tr>
                    </thead>
                    <tbody>
                        {KNOWLEDGE_ITEMS.map((item) => (
                            <tr key={item.id} className="border-b border-fkt-elevated/50 hover:bg-fkt-elevated transition-colors cursor-pointer group">
                                <td className="p-4 font-mono text-[12px] text-fkt-text-dim group-hover:text-fkt-text-primary transition-colors">{item.id}</td>
                                <td className="p-4 text-fkt-text-primary">{item.topic}</td>
                                <td className="p-4 font-mono text-[10px] text-fkt-text-muted">{item.type}</td>
                                <td className="p-4 font-mono text-[12px] text-fkt-accent">{item.success}%</td>
                                <td className="p-4 font-mono text-[12px] text-fkt-text-muted">{item.reviews}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
