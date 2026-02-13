export interface PaginationState {
	page?: number;
	limit?: number;
	filters?: Record<string, any>;
	sort?: { field: string; order: 'asc' | 'desc' };
}

export function encodePaginationState(state: PaginationState): string {
	const json = JSON.stringify(state);
	return btoa(json); // base64 encode
}

export function decodePaginationState(token: string): PaginationState {
	try {
		const json = atob(token); // base64 decode
		return JSON.parse(json);
	} catch {
		return { page: 1, limit: 5 }; // defaults
	}
}

export const DEFAULT_PAGINATION_STATE: PaginationState = {
	page: 1,
	limit: 5
};
