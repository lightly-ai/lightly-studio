import { describe, expect, it } from 'vitest';
import { getSceneUpdateExportScope } from './sceneUpdateExportScope';

describe('getSceneUpdateExportScope', () => {
    it('scopes to the open sequence when given one', () => {
        expect(getSceneUpdateExportScope('sequence-1', null)).toEqual({
            sequence_id: 'sequence-1'
        });
    });

    it('falls back to the MCAP sequence filter without an open sequence', () => {
        const filter = { filter_type: 'mcap_sequence' as const };
        expect(getSceneUpdateExportScope(undefined, filter)).toEqual({
            mcap_sequence_filter: filter
        });
    });
});
