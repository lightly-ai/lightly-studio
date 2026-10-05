import { describe, expect, it, vi } from 'vitest';
import { applyUiActions } from './applyUiActions';

describe('applyUiActions', () => {
    it('applies the actions in their order', async () => {
        const calls: string[] = [];
        const handlers = {
            showTag: vi.fn(async (tagId: string) => {
                calls.push(`tag:${tagId}`);
            }),
            showSamples: vi.fn((sampleIds: string[]) => {
                calls.push(`samples:${sampleIds.join(',')}`);
            }),
            refreshData: vi.fn(async () => {
                calls.push('refresh');
            })
        };

        await applyUiActions(
            [
                { type: 'show_samples', sample_ids: ['s1', 's2'] },
                { type: 'refresh_data' },
                { type: 'select_tag', tag_id: 't1', tag_name: 'tiger' }
            ],
            handlers
        );

        expect(calls).toEqual(['samples:s1,s2', 'refresh', 'tag:t1']);
    });
});
