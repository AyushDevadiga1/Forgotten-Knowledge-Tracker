/**
 * Typed API client — all calls go to /api/v1/* 
 * which Vite proxies to Flask at port 5000.
 */

const BASE = '/api/v1'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    })
    if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error ?? `HTTP ${res.status}`)
    }
    return res.json() as Promise<T>
}

// ── Types ────────────────────────────────────────────────
export interface LearningItem {
    id: string
    question: string
    answer: string
    difficulty: 'easy' | 'medium' | 'hard'
    item_type: string
    tags: string[]
    total_reviews: number
    correct_count: number
    success_rate: number
    next_review_date: string
    status: string
}

export interface Stats {
    total_items: number
    active_items: number
    mastered_items: number
    total_reviews: number
    average_success_rate: number
    items_due_today: number
    current_streak: number
}

export interface StatsResponse {
    success: boolean
    data: { stats: Stats; today: { reviews_today: number; concepts_studied: number } }
}

export interface TrendDay {
    date: string
    reviews: number
    correct: number
    added: number
    mastered: number
    due: number
    accuracy: number
}

export interface ItemsResponse {
    success: boolean
    data: LearningItem[]
    count: number
}

export interface DueResponse {
    success: boolean
    data: LearningItem[]
    count: number
}

export interface IntentPrediction {
    id: number
    timestamp: string
    predicted_intent: string
    confidence: number
    user_feedback: number | null
    window_title: string | null
}

export interface SessionStatus {
    active: boolean
    started_at: string | null
    stopped_at: string | null
    elapsed_seconds: number | null
}

// ── API Functions ────────────────────────────────────────
export const api = {
    /** GET /api/v1/stats */
    getStats: () => apiFetch<StatsResponse>('/stats'),

    /** GET /api/v1/stats/trend?days=N — real per-day time-series for sparklines */
    getStatsTrend: (days = 7) =>
        apiFetch<{ success: boolean; data: TrendDay[] }>(`/stats/trend?days=${days}`),

    /** GET /api/v1/items?status=all&limit=100 */
    getItems: (status = 'all', limit = 100) =>
        apiFetch<ItemsResponse>(`/items?status=${status}&limit=${limit}`),

    /** GET /api/v1/items/due */
    getDueItems: () => apiFetch<DueResponse>('/items/due'),

    /** GET /api/v1/items/:id */
    getItem: (id: string) => apiFetch<{ success: boolean; data: LearningItem }>(`/items/${id}`),

    /** POST /api/v1/reviews */
    recordReview: (item_id: string, quality: number) =>
        apiFetch<{ success: boolean }>('/reviews', {
            method: 'POST',
            body: JSON.stringify({ item_id, quality }),
        }),

    /** POST /api/v1/items */
    createItem: (payload: {
        question: string
        answer: string
        difficulty: string
        item_type: string
        tags: string[]
    }) =>
        apiFetch<{ success: boolean; data: { id: string } }>('/items', {
            method: 'POST',
            body: JSON.stringify(payload),
        }),

    /** GET /api/v1/intent/recent */
    getRecentIntent: () => apiFetch<{ success: boolean; data: IntentPrediction | null }>('/intent/recent'),

    /** POST /api/v1/intent/feedback */
    sendIntentFeedback: (prediction_id: number, is_correct: boolean, actual_intent?: string) =>
        apiFetch<{ success: boolean }>('/intent/feedback', {
            method: 'POST',
            body: JSON.stringify({ prediction_id, is_correct, actual_intent }),
        }),

    /** GET /api/v1/session/status */
    getSessionStatus: () =>
        apiFetch<{ success: boolean; data: SessionStatus }>('/session/status'),

    /** POST /api/v1/session/start */
    startSession: () =>
        apiFetch<{ success: boolean; data: SessionStatus }>('/session/start', {
            method: 'POST',
            body: JSON.stringify({}),
        }),

    /** POST /api/v1/session/stop */
    stopSession: () =>
        apiFetch<{ success: boolean; data: SessionStatus }>('/session/stop', {
            method: 'POST',
            body: JSON.stringify({}),
        }),

    /** GET /api/v1/graph/stats */
    getGraphStats: () => apiFetch<{ success: boolean; data: GraphStats }>('/graph/stats'),

    /** GET /api/v1/graph/gaps?limit=N */
    getKnowledgeGaps: (limit = 8) =>
        apiFetch<{ success: boolean; data: KnowledgeGap[]; count: number }>(`/graph/gaps?limit=${limit}`),

    /** GET /api/v1/quiz/current */
    getQuiz: () => apiFetch<{ success: boolean; data: QuizQuestion | null }>('/quiz/current'),

    /** POST /api/v1/quiz/answer */
    submitQuizAnswer: (concept: string, was_correct: boolean) =>
        apiFetch<{ success: boolean; message: string }>('/quiz/answer', {
            method: 'POST',
            body: JSON.stringify({ concept, was_correct }),
        }),

    /** GET /api/v1/health */
    health: () => apiFetch<{ status: string }>('/health'),
}

// ── Graph + Quiz Types ────────────────────────────────────
export interface GraphEdge {
    source: string
    target: string
    weight: number
}

export interface GraphStats {
    total_concepts: number
    total_edges: number
    avg_memory_strength: number
    top_concepts: string[]
    edges: GraphEdge[]
}

export interface KnowledgeGap {
    concept: string
    last_seen: string
    memory_strength: number
    gap_score: number
}

export interface QuizQuestion {
    concept: string
    question: string
    options: string[]
    correct_answer: string
    difficulty: string
}
