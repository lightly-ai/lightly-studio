import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePointCloudNavigation } from './usePointCloudNavigation.svelte';

const { gotoMock } = vi.hoisted(() => ({ gotoMock: vi.fn() }));

vi.mock('$app/navigation', () => ({ goto: gotoMock }));

describe('usePointCloudNavigation', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('navigates to the point-cloud labeling route', () => {
        const { navigate } = usePointCloudNavigation();

        expect(
            navigate({
                datasetId: 'dataset',
                collectionId: 'collection',
                sampleId: 'sample',
                groupId: 'group'
            })
        ).toBe(true);
        expect(gotoMock).toHaveBeenCalledWith(
            '/datasets/dataset/group/collection/point-clouds/sample?group_id=group',
            { invalidateAll: true }
        );
    });
});
