import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
import { routeHelpers } from '$lib/routes';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SampleType } from '$lib/api/lightly_studio_local';
import type { PageLoadEvent } from './$types';
import { load } from './+page';

const { gotoMock } = vi.hoisted(() => ({
    gotoMock: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local/sdk.gen');
vi.mock('$app/navigation', () => ({
    goto: gotoMock
}));

describe('+page.ts', () => {
    const mockDatasetId = '123e4567-e89b-12d3-a456-426614174000';

    beforeEach(() => {
        vi.clearAllMocks();
        gotoMock.mockClear();
        vi.mocked(readCollection).mockReset();
    });

    it('should navigate to samples for IMAGE collection', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: {
                collection_id: mockDatasetId,
                name: 'Test Dataset',
                sample_type: SampleType.IMAGE,
                parent_collection_id: null
            },
            request: undefined,
            response: undefined
        });

        void load({
            params: { dataset_id: mockDatasetId }
        } as PageLoadEvent);

        await vi.waitFor(() => {
            expect(gotoMock).toHaveBeenCalledWith(
                routeHelpers.toSamples(mockDatasetId, 'image', mockDatasetId)
            );
        });
    });

    it('should navigate to videos for VIDEO collection', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: {
                collection_id: mockDatasetId,
                name: 'Test Video Dataset',
                sample_type: SampleType.VIDEO,
                parent_collection_id: null
            },
            request: undefined,
            response: undefined
        });

        void load({
            params: { dataset_id: mockDatasetId }
        } as PageLoadEvent);

        await vi.waitFor(() => {
            expect(gotoMock).toHaveBeenCalledWith(
                routeHelpers.toVideos(mockDatasetId, 'video', mockDatasetId)
            );
        });
    });

    it('should navigate to groups for GROUP collection', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: {
                collection_id: mockDatasetId,
                name: 'Test Group Dataset',
                sample_type: SampleType.GROUP,
                parent_collection_id: null
            },
            request: undefined,
            response: undefined
        });

        void load({
            params: { dataset_id: mockDatasetId }
        } as PageLoadEvent);

        await vi.waitFor(() => {
            expect(gotoMock).toHaveBeenCalledWith(
                routeHelpers.toGroups(mockDatasetId, 'group', mockDatasetId)
            );
        });
    });

    it('should navigate to home when collection not found', async () => {
        vi.mocked(readCollection).mockRejectedValue(new Error('Not found'));

        void load({
            params: { dataset_id: mockDatasetId }
        } as PageLoadEvent);

        await vi.waitFor(() => {
            expect(gotoMock).toHaveBeenCalledWith(routeHelpers.toHome());
        });
    });

    it('should navigate to home when collection data is undefined', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: undefined,
            request: undefined,
            response: undefined
        });

        void load({
            params: { dataset_id: mockDatasetId }
        } as PageLoadEvent);

        await vi.waitFor(() => {
            expect(gotoMock).toHaveBeenCalledWith(routeHelpers.toHome());
        });
    });

    it('should navigate to home when collection is not a root', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: {
                collection_id: mockDatasetId,
                name: 'Child Collection',
                sample_type: SampleType.IMAGE,
                parent_collection_id: 'test-parent-id'
            },
            request: undefined,
            response: undefined
        });

        void load({
            params: { dataset_id: mockDatasetId }
        } as PageLoadEvent);

        await vi.waitFor(() => {
            expect(gotoMock).toHaveBeenCalledWith(routeHelpers.toHome());
        });
    });

    it('should navigate to home for invalid root collection type (ANNOTATION)', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: {
                collection_id: mockDatasetId,
                name: 'Annotation Collection',
                sample_type: SampleType.ANNOTATION,
                parent_collection_id: null
            },
            request: undefined,
            response: undefined
        });

        void load({
            params: { dataset_id: mockDatasetId }
        } as PageLoadEvent);

        await vi.waitFor(() => {
            expect(gotoMock).toHaveBeenCalledWith(routeHelpers.toHome());
        });
    });
});
