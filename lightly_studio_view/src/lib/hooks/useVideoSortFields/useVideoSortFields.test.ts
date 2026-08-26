import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MetadataInfoView } from '$lib/api/lightly_studio_local';
import { useVideoSortFields } from './useVideoSortFields';

const metadataInfo = writable<MetadataInfoView[]>([]);

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({ metadataInfo })
}));

describe('useVideoSortFields', () => {
    beforeEach(() => {
        metadataInfo.set([]);
    });

    describe('allSortFields', () => {
        it('contains the seven base video sort fields', () => {
            const { allSortFields } = useVideoSortFields();
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({ source: 'video', value: 'file_name' }),
                    expect.objectContaining({ source: 'video', value: 'file_path_abs' }),
                    expect.objectContaining({ source: 'video', value: 'created_at' }),
                    expect.objectContaining({ source: 'video', value: 'width' }),
                    expect.objectContaining({ source: 'video', value: 'height' }),
                    expect.objectContaining({ source: 'video', value: 'duration_s' }),
                    expect.objectContaining({ source: 'video', value: 'fps' })
                ])
            );
        });

        it('includes metadata fields of supported types with metadata. prefix label', () => {
            metadataInfo.set([
                { name: 'score', type: 'float' },
                { name: 'count', type: 'integer' },
                { name: 'label', type: 'string' },
                { name: 'active', type: 'boolean' }
            ]);
            const { allSortFields } = useVideoSortFields();
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'score',
                        label: 'metadata.score'
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'count',
                        label: 'metadata.count'
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'label',
                        label: 'metadata.label'
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'active',
                        label: 'metadata.active'
                    })
                ])
            );
        });

        it('excludes list and dict metadata fields', () => {
            metadataInfo.set([
                { name: 'tags', type: 'list' },
                { name: 'nested', type: 'dict' },
                { name: 'score', type: 'float' }
            ]);
            const { allSortFields } = useVideoSortFields();
            const fields = get(allSortFields);

            expect(fields.map((f) => f.value)).not.toContain('tags');
            expect(fields.map((f) => f.value)).not.toContain('nested');
        });

        it('updates reactively when metadataInfo changes', () => {
            const { allSortFields } = useVideoSortFields();

            expect(get(allSortFields).find((f) => f.value === 'brightness')).toBeUndefined();

            metadataInfo.set([{ name: 'brightness', type: 'float' }]);

            expect(get(allSortFields).find((f) => f.value === 'brightness')).toBeDefined();
        });
    });
});
