import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PageLoadEvent } from './$types';
import { load } from './+page';
import { routeHelpers } from '$lib/routes';
import { SampleType } from '$lib/api/lightly_studio_local';

vi.mock('$lib/api/lightly_studio_local/sdk.gen');
vi.mock('@sveltejs/kit', () => ({
    redirect: vi.fn((status, location) => {
        const error = new Error('Redirect') as Error & { status: number; location: string };
        error.status = status;
        error.location = location;
        throw error;
    })
}));

type RedirectError = Error & { status: number; location: string };

describe('+page.ts', () => {
    const mockDatasetId = '123e4567-e89b-12d3-a456-426614174000';

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should redirect to samples for IMAGE collection', async () => {
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

        try {
            await load({
                params: { dataset_id: mockDatasetId }
            } as PageLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(
                routeHelpers.toSamples(mockDatasetId, 'image', mockDatasetId)
            );
        }
    });

    it('should redirect to videos for VIDEO collection', async () => {
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

        try {
            await load({
                params: { dataset_id: mockDatasetId }
            } as PageLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(
                routeHelpers.toVideos(mockDatasetId, 'video', mockDatasetId)
            );
        }
    });

    it('should redirect to groups for GROUP collection', async () => {
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

        try {
            await load({
                params: { dataset_id: mockDatasetId }
            } as PageLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(
                routeHelpers.toGroups(mockDatasetId, 'group', mockDatasetId)
            );
        }
    });

    it('should redirect to home when collection not found', async () => {
        vi.mocked(readCollection).mockRejectedValue(new Error('Not found'));

        try {
            await load({
                params: { dataset_id: mockDatasetId }
            } as PageLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect to home when collection data is undefined', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: undefined,
            request: undefined,
            response: undefined
        });

        try {
            await load({
                params: { dataset_id: mockDatasetId }
            } as PageLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect to home when collection is not a root)', async () => {
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

        try {
            await load({
                params: { dataset_id: mockDatasetId }
            } as PageLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect to home for invalid root collection type (ANNOTATION)', async () => {
        vi.mocked(readCollection).mockResolvedValue({
            data: {
                collection_id: mockDatasetId,
                name: 'Annotation Collection',
                sample_type: SampleType.ANNOTATION,
                parent_collection_id: 'test-parent-id'
            },
            request: undefined,
            response: undefined
        });

        try {
            await load({
                params: { dataset_id: mockDatasetId }
            } as PageLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });
});
