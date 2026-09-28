import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js';
import { useVideoClassDistributionSource } from './useVideoClassDistributionSource.svelte';

vi.mock('$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js', () => ({
    useVideoAnnotationCounts: vi.fn()
}));

const count = (label_name: string, current_count: number) => ({
    label_name,
    current_count,
    total_count: current_count
});

const allCounts = [count('car', 5), count('road', 3)];
const classificationCounts = [count('road', 3)];
const detectionCounts = [count('car', 4)];

const mockCounts = (countsByType: Map<AnnotationType | undefined, unknown[]>) => {
    // A disabled query never fetches, so it has no data.
    vi.mocked(useVideoAnnotationCounts).mockImplementation((getParams) => {
        const { annotationType, enabled } = getParams();
        return {
            data: enabled ? countsByType.get(annotationType) : undefined,
            isFetching: false
        } as unknown as ReturnType<typeof useVideoAnnotationCounts>;
    });
};

const defaultParams = {
    collectionId: 'collection-1',
    filter: undefined,
    selectedClassNames: ['car'],
    allSourcesHidden: false,
    active: true
};

const renderHook = (params: Partial<typeof defaultParams> = {}) =>
    useVideoClassDistributionSource(() => ({ ...defaultParams, ...params }));

describe('useVideoClassDistributionSource', () => {
    beforeEach(() => {
        mockCounts(
            new Map<AnnotationType | undefined, unknown[]>([
                [undefined, allCounts],
                [AnnotationType.CLASSIFICATION, classificationCounts],
                [AnnotationType.OBJECT_DETECTION, detectionCounts],
                [AnnotationType.SEGMENTATION_MASK, []]
            ])
        );
    });

    it('groups video counts by annotation type and skips empty types', () => {
        const { source } = renderHook();

        expect(source.valueNoun).toBe('videos');
        expect(source.groups?.map(({ label, data }) => ({ label, data }))).toEqual([
            {
                label: 'All types',
                data: [
                    { label: 'car', count: 5, selected: true },
                    { label: 'road', count: 3, selected: false }
                ]
            },
            { label: 'Classification', data: [{ label: 'road', count: 3, selected: false }] },
            { label: 'Object detection', data: [{ label: 'car', count: 4, selected: true }] }
        ]);
    });

    it('drops the type picker when only one type has counts', () => {
        mockCounts(
            new Map<AnnotationType | undefined, unknown[]>([
                [undefined, detectionCounts],
                [AnnotationType.OBJECT_DETECTION, detectionCounts]
            ])
        );

        const { source } = renderHook();

        expect(source.groups).toBeUndefined();
        expect(source.data).toEqual([{ label: 'car', count: 4, selected: true }]);
    });

    it('shows no counts when every annotation source is hidden', () => {
        const { source } = renderHook({ allSourcesHidden: true });

        expect(source.groups).toBeUndefined();
        expect(source.data).toEqual([]);
    });

    it('does not fetch counts while another source is shown', () => {
        const { source } = renderHook({ active: false });

        expect(source.data).toEqual([]);
    });
});
