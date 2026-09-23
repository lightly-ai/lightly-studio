import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { usePointCloudNavigation } from './usePointCloudNavigation.svelte';

const { gotoMock } = vi.hoisted(() => ({ gotoMock: vi.fn() }));
const featureFlags = writable<string[]>([]);

vi.mock('$app/navigation', () => ({ goto: gotoMock }));
vi.mock('$lib/hooks', () => ({ useFeatureFlags: () => ({ featureFlags }) }));

describe('usePointCloudNavigation', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        featureFlags.set([]);
    });

    it('does not navigate when point-cloud labeling is disabled', () => {
        const { navigate } = usePointCloudNavigation();

        expect(
            navigate({ datasetId: 'dataset', collectionId: 'collection', sampleId: 'sample', groupId: 'group' })
        ).toBe(false);
        expect(gotoMock).not.toHaveBeenCalled();
    });

    it('navigates to the point-cloud labeling route when enabled', () => {
        featureFlags.set(['point_cloud_labeling']);
        const { navigate } = usePointCloudNavigation();

        expect(
            navigate({ datasetId: 'dataset', collectionId: 'collection', sampleId: 'sample', groupId: 'group' })
        ).toBe(true);
        expect(gotoMock).toHaveBeenCalledWith(
            '/datasets/dataset/point-clouds/collection/sample?sequence_id=sample&collection_type=group&group_id=group',
            { invalidateAll: true }
        );
    });
});
