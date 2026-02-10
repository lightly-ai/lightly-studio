export interface PaginationState {
    offset: number;
    limit: number;
}

export function decodePaginationHash(hash: string): PaginationState {
    try {
        if (!hash || hash === '#') {
            return { offset: 0, limit: 20 };
        }
        const decoded = atob(hash.replace('#', ''));
        return JSON.parse(decoded);
    } catch {
        return { offset: 0, limit: 20 };
    }
}

export function encodePaginationHash(state: PaginationState): string {
    return '#' + btoa(JSON.stringify(state));
}
