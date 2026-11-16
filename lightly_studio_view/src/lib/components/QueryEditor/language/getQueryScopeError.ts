import type { Query } from './generated/ast';

/** Check that a parsed query belongs to the active collection. */
export function getQueryScopeError(query: Query, sampleType?: 'image' | 'video') {
    const scope = query.isVideo ? 'video' : 'image';
    if (sampleType && scope !== sampleType) {
        return 'Video queries cannot be applied to an image collection.';
    }
}
