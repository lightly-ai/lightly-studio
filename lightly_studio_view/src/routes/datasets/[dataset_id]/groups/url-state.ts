/**
 * Generic URL State Management System using Base64-encoded hash
 *
 * ADVANTAGES OVER QUERY PARAMETERS:
 * - Clean URLs: `/groups#abc123` vs `/groups?offset=20&limit=10&tags=a,b,c&view=grid`
 * - More capacity: 10KB+ vs ~2KB practical limit for query params
 * - No server roundtrips: Hash changes don't reload the page or hit the server
 * - Type-safe: Full TypeScript support with interfaces
 * - Shareable: URLs preserve exact application state
 * - Browser history friendly: Hash changes work with back/forward without page reloads
 * - Extensible: Add new state fields without breaking existing URLs
 * - Backward compatible: Old URLs with missing fields get sensible defaults
 * - Privacy friendly: Hash fragments aren't sent to server in HTTP requests
 *
 * COMPARISON TO CURRENT APPROACH:
 *
 * Query Parameters (Current):
 *   URL: /groups?offset=20&limit=10&tags=tag1,tag2&search=foo&sort=name&order=asc
 *   - Length: ~80 chars for basic state
 *   - Readability: Visible but verbose
 *   - Each change: Server request + full page reload (unless using replaceState)
 *   - Practical limit: ~2KB (safe cross-browser, especially with proxies/CDNs)
 *   - Example: 10 filters = ~200 chars, 50 filters = ~1KB (approaching limits)
 *   - Encoding issues: Special chars need URL encoding (%20, %3A, etc.)
 *   - Server logs: All state visible in server logs (privacy concern)
 *
 * Base64 Hash (This approach):
 *   URL: /groups#eyJwYWdpbmF0aW9uIjp7Im9mZnNldCI6MjB9fQ
 *   - Length: ~45 chars for same state (cleaner)
 *   - Readability: Opaque but decodable
 *   - Each change: No server request, instant client-side update
 *   - Practical limit: ~10KB safe, up to 65KB+ supported
 *   - Example: 10 filters = ~400 chars, 500+ filters = ~8KB (still comfortable)
 *   - Encoding: Base64 (safe, standard, no special char issues)
 *   - Server logs: Hash never sent to server (better privacy)
 *
 * DATA CAPACITY:
 * - URL length limits vary by browser:
 *   - Chrome/Edge: ~2MB total URL length (practical limit ~32KB for hash)
 *   - Firefox: ~65KB for entire URL
 *   - Safari: ~80KB for entire URL
 *   - IE11: ~2KB (legacy, rarely relevant)
 *
 * - Base64 encoding overhead: ~33% larger (4 chars per 3 bytes of JSON)
 * - Practical recommendation: Keep state under 10KB (~7.5KB raw JSON)
 * - Example capacity at 10KB:
 *   - ~500 filter items with IDs and names
 *   - ~1000 simple numeric values
 *   - Complex state with pagination + filters + sorts + selections + view prefs
 *
 * REAL-WORLD SIZE EXAMPLES:
 * - Pagination only: {"pagination":{"offset":20,"limit":10}} = 44 chars → 60 chars base64
 * - With filters: +50 tags = ~600 chars base64
 * - With selections: +100 selected IDs = ~1.2KB base64
 * - Full UI state: ~2-4KB base64 (very comfortable)
 *
 * WHAT YOU CAN STORE:
 * - Pagination state (offset, limit, page)
 * - Filter selections (tags, metadata, date ranges)
 * - Sort configurations (field, direction)
 * - View preferences (grid/list, column visibility)
 * - Search queries and parameters
 * - Selected items/IDs (hundreds to thousands)
 * - UI state (collapsed panels, active tabs, zoom)
 * - Visualization settings (color schemes, layouts)
 *
 * OPTIMIZATION NOTES:
 * - For even larger state, consider:
 *   1. Use short property names (p instead of pagination)
 *   2. Omit default values (saves ~30-50%)
 *   3. Add LZ-string compression for very large state (can achieve 5-10x compression)
 *   4. Store large datasets server-side and reference by ID
 *   5. Split rarely-changed state into separate storage (localStorage)
 */

export interface PaginationState {
    offset: number;
    limit: number;
}

export interface FilterState {
    tags?: string[];
    search?: string;
    dateFrom?: string;
    dateTo?: string;
}

export interface ViewState {
    viewMode?: 'grid' | 'list';
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
}

// Combined state interface - extend this as needed
export interface UrlState {
    pagination?: PaginationState;
    filters?: FilterState;
    view?: ViewState;
    // Add more state categories here
}

const DEFAULT_STATE: UrlState = {
    pagination: { offset: 0, limit: 20 }
};

/**
 * Decode URL hash into typed state object
 * @param hash - URL hash string (with or without #)
 * @returns Parsed state object with defaults for missing fields
 */
export function decodeUrlState(hash: string): UrlState {
    try {
        if (!hash || hash === '#') {
            return { ...DEFAULT_STATE };
        }
        const decoded = atob(hash.replace('#', ''));
        const parsed = JSON.parse(decoded);

        // Merge with defaults to handle missing fields
        return {
            pagination: parsed.pagination || DEFAULT_STATE.pagination,
            filters: parsed.filters,
            view: parsed.view
        };
    } catch {
        return { ...DEFAULT_STATE };
    }
}

/**
 * Encode state object into base64 hash
 * @param state - State object to encode
 * @returns Base64-encoded hash string with # prefix
 */
export function encodeUrlState(state: UrlState): string {
    // Remove undefined/null values to minimize size
    const cleaned = JSON.parse(JSON.stringify(state));
    return '#' + btoa(JSON.stringify(cleaned));
}

// Backward compatibility helpers for existing pagination-only code
export function decodePaginationHash(hash: string): PaginationState {
    const state = decodeUrlState(hash);
    return state.pagination || DEFAULT_STATE.pagination!;
}

export function encodePaginationHash(pagination: PaginationState): string {
    return encodeUrlState({ pagination });
}

/**
 * Update a specific part of the URL state
 * @param currentHash - Current hash value
 * @param updates - Partial state updates
 * @returns New hash with merged state
 */
export function updateUrlState(currentHash: string, updates: Partial<UrlState>): string {
    const current = decodeUrlState(currentHash);
    const merged = {
        ...current,
        ...updates,
        // Deep merge nested objects
        pagination: updates.pagination ? { ...current.pagination, ...updates.pagination } : current.pagination,
        filters: updates.filters ? { ...current.filters, ...updates.filters } : current.filters,
        view: updates.view ? { ...current.view, ...updates.view } : current.view
    };
    return encodeUrlState(merged);
}
