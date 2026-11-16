import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import { APP_ROUTES } from '$lib/routes';
import { useVideoFramesBounds } from '$lib/hooks';
import OperatorDialog from './OperatorDialog.svelte';

const { page } = await vi.hoisted(async () => {
    const { writable } = await import('svelte/store');
    return {
        page: writable<{ route: { id: string | null }; params: Record<string, string> }>({
            route: { id: '' },
            params: {}
        })
    };
});

vi.mock('$app/stores', () => ({ page }));
vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: vi.fn() })
}));
vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local')>()),
    readTags: vi.fn().mockResolvedValue({ data: [] })
}));
vi.mock('$lib/hooks/usePostHog', () => ({ usePostHog: () => ({ trackEvent: vi.fn() }) }));

const setPage = (routeId: string | null, collectionType: string, collectionId: string) =>
    page.set({
        route: { id: routeId },
        params: {
            dataset_id: 'dataset-1',
            collection_type: collectionType,
            collection_id: collectionId
        }
    });

describe('OperatorDialog', () => {
    it('follows the filters of the current page after navigation', async () => {
        const frames = useVideoFramesBounds();
        frames.updateVideoFramesBounds({ frame_number: { min: 0, max: 100 } });
        frames.updateVideoFramesBoundsValues({ frame_number: { min: 0, max: 100 } });
        setPage(APP_ROUTES.videos, 'video', 'videos-1');

        render(OperatorDialog, {
            props: { operatorMetadata: null, isOpen: true, onOpenChange: vi.fn() }
        });
        expect(await screen.findByText('all 0 videos')).toBeInTheDocument();

        setPage(APP_ROUTES.frames, 'video_frame', 'frames-1');
        frames.updateVideoFramesBoundsValues({ frame_number: { min: 10, max: 100 } });

        await waitFor(() =>
            expect(screen.getByText('0 filtered video frames')).toBeInTheDocument()
        );
    });
});
