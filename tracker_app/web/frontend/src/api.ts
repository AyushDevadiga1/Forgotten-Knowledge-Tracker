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
    tags: string
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

// ── API Functions ────────────────────────────────────────
export const api = {
    /** GET /api/v1/stats */
    getStats: () => apiFetch<StatsResponse>('/stats'),

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
}
