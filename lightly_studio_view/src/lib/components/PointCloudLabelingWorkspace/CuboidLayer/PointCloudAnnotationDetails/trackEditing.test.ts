import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { QueryClient } from '@tanstack/svelte-query';
import type { ComponentProps } from 'svelte';
import { getTracksQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import TrackEditingHarness from './TrackEditingHarness.svelte';

const { updateAnnotations, updateParentTrack, refetchTracks } = vi.hoisted(() => ({
    updateAnnotations: vi.fn(),
    updateParentTrack: vi.fn(),
    refetchTracks: vi.fn()
}));
let serverTracks: TrackWithClassNameView[] = [];
let queryClient: QueryClient;
function setServerTracks(data: TrackWithClassNameView[]) {
    serverTracks = data;
}
vi.mock('$lib/hooks/useUpdateTrackMutation/useUpdateTrackMutation.svelte', () => ({
    useUpdateTrackMutation: () => ({
        updateParentTrack: async (trackId: string, parentTrackId: string | null) => {
            await updateParentTrack({
                path: { dataset_id: 'ds-1', track_id: trackId },
                body: { parent_object_track_id: parentTrackId }
            });
        },
        get isPending() {
            return false;
        }
    })
}));
vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    getTracks: async (...args: unknown[]) => {
        await refetchTracks(...args);
        return { data: serverTracks };
    },
    updateAnnotations: async (...args: unknown[]) => {
        await updateAnnotations(...args);
        return { data: [] };
    },
    updateTrack: async (...args: unknown[]) => {
        await updateParentTrack(...args);
        return { data: {} };
    },
    getFeatures: async () => ({ data: [] }),
    getAnalyticsConfig: async () => ({ data: undefined })
}));
vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/pointCloudWorkspaceLayoutContext.svelte',
    () => ({ usePointCloudWorkspaceLayoutContext: () => () => ({ datasetId: 'ds-1' }) })
);

const currentTrack = {
    object_track_id: 'track-0',
    object_track_number: 7,
    annotation_class_name: 'car',
    parent_object_track_id: null
};
const parentTrack = {
    object_track_id: 'parent',
    object_track_number: 1,
    annotation_class_name: 'car',
    parent_object_track_id: null
};
const defaultProps = { annotation: createAnnotationFixture(), editable: true };

interface RenderDetailsParams {
    props: Omit<ComponentProps<typeof TrackEditingHarness>, 'client'>;
}

function renderDetails({ props }: RenderDetailsParams) {
    queryClient.setQueryData(getTracksQueryKey({ path: { dataset_id: 'ds-1' } }), serverTracks);
    return render(TrackEditingHarness, { props: { ...props, client: queryClient } });
}

function expectSelectorsDisabled(disabled: boolean) {
    for (const selector of screen.getAllByRole('combobox')) {
        expect(selector).toHaveProperty('disabled', disabled);
    }
}

async function chooseTrack(operation: string) {
    const user = userEvent.setup();
    await user.click(screen.getAllByRole('combobox')[operation === 'assignment' ? 0 : 1]);
    await user.click(screen.getByRole('option', { name: 'car - 1' }));
}

describe('track editing refresh lifecycle', () => {
    afterEach(() => {
        queryClient.clear();
    });
    beforeEach(() => {
        vi.resetAllMocks();
        queryClient = new QueryClient({
            defaultOptions: {
                queries: { retry: false, staleTime: Infinity },
                mutations: { retry: false }
            }
        });
        setServerTracks([currentTrack, parentTrack]);
        Element.prototype.scrollIntoView = vi.fn();
    });

    it.each([
        ['assignment', 'tracks'],
        ['assignment', 'annotation'],
        ['parent', 'tracks'],
        ['parent', 'annotation']
    ])(
        'keeps both selectors disabled for %s when %s refresh finishes first',
        async (operation, firstRefresh) => {
            const save = Promise.withResolvers<void>();
            const trackRefresh = Promise.withResolvers<void>();
            const annotationRefresh = Promise.withResolvers<void>();
            updateAnnotations.mockReturnValue(save.promise);
            updateParentTrack.mockReturnValue(save.promise);
            refetchTracks.mockReturnValue(trackRefresh.promise);
            const onTrackChange = vi.fn(() => annotationRefresh.promise);
            const view = renderDetails({
                props: { ...defaultProps, onTrackChange }
            });

            await chooseTrack(operation);
            expectSelectorsDisabled(true);
            save.resolve();
            await waitFor(() => expect(refetchTracks).toHaveBeenCalled());
            expectSelectorsDisabled(true);
            await waitFor(() => expect(onTrackChange).toHaveBeenCalled());
            if (firstRefresh === 'tracks') {
                setServerTracks([parentTrack, { ...currentTrack, object_track_id: 'replacement' }]);
                trackRefresh.resolve();
            } else {
                await view.rerender({
                    annotation: { ...defaultProps.annotation, trackId: 'replacement' }
                });
                annotationRefresh.resolve();
            }
            await Promise.resolve();
            expectSelectorsDisabled(true);

            setServerTracks([parentTrack, { ...currentTrack, object_track_id: 'replacement' }]);
            await view.rerender({
                annotation: { ...defaultProps.annotation, trackId: 'replacement' }
            });
            trackRefresh.resolve();
            annotationRefresh.resolve();
            await waitFor(() => expectSelectorsDisabled(false));
        }
    );

    it('uses the replacement annotation track for the next parent edit', async () => {
        let revision = 0;
        const onTrackChange = async () => {
            revision += 1;
            const trackId = `replacement-${revision}`;
            setServerTracks([
                parentTrack,
                {
                    ...currentTrack,
                    object_track_id: trackId,
                    parent_object_track_id: revision === 1 ? 'parent' : null
                }
            ]);
            await view.rerender({ annotation: { ...defaultProps.annotation, trackId } });
        };
        const view = renderDetails({
            props: { ...defaultProps, onTrackChange }
        });

        await chooseTrack('parent');
        await waitFor(() => expectSelectorsDisabled(false));
        const user = userEvent.setup();
        await user.click(screen.getAllByRole('combobox')[1]);
        await user.click(screen.getByRole('option', { name: 'No parent' }));
        await waitFor(() => expectSelectorsDisabled(false));

        expect(updateParentTrack).toHaveBeenNthCalledWith(
            1,
            expect.objectContaining({
                path: { dataset_id: 'ds-1', track_id: 'track-0' },
                body: { parent_object_track_id: 'parent' }
            })
        );
        expect(updateParentTrack).toHaveBeenNthCalledWith(
            2,
            expect.objectContaining({
                path: { dataset_id: 'ds-1', track_id: 'replacement-1' },
                body: { parent_object_track_id: null }
            })
        );
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it.each(['assignment', 'parent'])('allows retrying a failed %s mutation', async (operation) => {
        const mutation = operation === 'assignment' ? updateAnnotations : updateParentTrack;
        mutation.mockRejectedValueOnce(new Error('save failed'));
        renderDetails({
            props: { ...defaultProps, onTrackChange: async () => {} }
        });

        await chooseTrack(operation);
        expect(await screen.findByRole('alert')).toHaveTextContent('Failed to save track changes');
        await waitFor(() => expectSelectorsDisabled(false));

        await chooseTrack(operation);
        await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
        await waitFor(() => expectSelectorsDisabled(false));
        expect(mutation).toHaveBeenCalledTimes(2);
    });

    it.each([
        ['assignment', 'tracks'],
        ['assignment', 'annotation'],
        ['parent', 'tracks'],
        ['parent', 'annotation']
    ])('recovers a failed %s %s refresh without repeating the save', async (operation, failure) => {
        const replacement = {
            ...currentTrack,
            object_track_id: 'replacement',
            parent_object_track_id: 'parent'
        };
        const onTrackChange = vi.fn(async () => {
            if (failure === 'annotation' && onTrackChange.mock.calls.length === 1) {
                throw new Error('annotation refresh failed');
            }
            await view.rerender({
                annotation: { ...defaultProps.annotation, trackId: 'replacement' }
            });
        });
        refetchTracks.mockImplementation(async () => {
            if (failure === 'tracks' && refetchTracks.mock.calls.length === 1) {
                throw new Error('track refresh failed');
            }
            setServerTracks([parentTrack, replacement]);
        });
        const view = renderDetails({
            props: { ...defaultProps, onTrackChange }
        });

        await chooseTrack(operation);
        expect(await screen.findByRole('alert')).toHaveTextContent('could not refresh');
        expectSelectorsDisabled(true);
        const retry = screen.getByRole('button', { name: 'Retry refresh' });
        expect(retry).not.toBeDisabled();
        await userEvent.setup().click(retry);
        await waitFor(() => expectSelectorsDisabled(false));
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        const mutation = operation === 'assignment' ? updateAnnotations : updateParentTrack;
        expect(mutation).toHaveBeenCalledOnce();
    });

    it('keeps a deleted annotation track blocked until a usable snapshot is refreshed', async () => {
        refetchTracks.mockImplementation(async () => {
            setServerTracks([parentTrack, { ...currentTrack, object_track_id: 'replacement' }]);
        });
        const view = renderDetails({
            props: { ...defaultProps, onTrackChange: async () => {} }
        });

        await chooseTrack('parent');
        expect(await screen.findByRole('alert')).toHaveTextContent('could not refresh');
        expectSelectorsDisabled(true);
        await view.rerender({
            annotation: { ...defaultProps.annotation, trackId: 'replacement' }
        });
        await userEvent.setup().click(screen.getByRole('button', { name: 'Retry refresh' }));
        await waitFor(() => expectSelectorsDisabled(false));
    });

    it('preserves occupied assignment filtering and excludes descendants only from parent choices', async () => {
        setServerTracks([
            {
                ...currentTrack,
                object_track_id: 'grandchild',
                object_track_number: 9,
                parent_object_track_id: 'child'
            },
            {
                ...currentTrack,
                object_track_id: 'child',
                object_track_number: 8,
                parent_object_track_id: 'track-0'
            },
            currentTrack,
            parentTrack
        ]);
        renderDetails({
            props: { ...defaultProps, occupiedTrackIds: new Set(['track-0', 'parent']) }
        });
        const user = userEvent.setup();
        await user.click(screen.getAllByRole('combobox')[0]);
        const assignments = screen
            .getAllByRole('option')
            .map((option) => option.textContent?.trim());
        expect(assignments).toEqual(['No track', 'car - 7', 'car - 8', 'car - 9', '+ New track']);
        await user.keyboard('{Escape}');
        await user.click(screen.getAllByRole('combobox')[1]);
        await waitFor(() => {
            const parents = screen
                .getAllByRole('option')
                .map((option) => option.textContent?.trim());
            expect(parents).toEqual(['No parent', 'car - 1']);
        });
    });

    it('filters available tracks by annotation class name', async () => {
        const personTrack = {
            object_track_id: 'person-track',
            object_track_number: 2,
            annotation_class_name: 'person',
            parent_object_track_id: null
        };
        const classlessTrack = {
            object_track_id: 'empty-track',
            object_track_number: 3,
            annotation_class_name: null,
            parent_object_track_id: null
        };
        setServerTracks([currentTrack, personTrack, classlessTrack]);
        renderDetails({
            props: {
                ...defaultProps,
                annotation: { ...defaultProps.annotation, annotationClassName: 'car' }
            }
        });
        const user = userEvent.setup();
        await user.click(screen.getAllByRole('combobox')[0]);
        const assignments = screen
            .getAllByRole('option')
            .map((option) => option.textContent?.trim());
        expect(assignments).toEqual(['No track', 'Track 3', 'car - 7', '+ New track']);
    });

    it('hides the current track when its class differs from the annotation', async () => {
        const mismatchedCurrentTrack = {
            object_track_id: 'track-0',
            object_track_number: 7,
            annotation_class_name: 'truck',
            parent_object_track_id: null
        };
        const matchingTrack = {
            object_track_id: 'matching',
            object_track_number: 2,
            annotation_class_name: 'car',
            parent_object_track_id: null
        };
        setServerTracks([mismatchedCurrentTrack, matchingTrack]);
        renderDetails({
            props: {
                ...defaultProps,
                annotation: { ...defaultProps.annotation, annotationClassName: 'car' }
            }
        });
        const user = userEvent.setup();
        await user.click(screen.getAllByRole('combobox')[0]);
        const assignments = screen
            .getAllByRole('option')
            .map((option) => option.textContent?.trim());
        expect(assignments).not.toContain('truck - 7');
        expect(assignments).toContain('car - 2');
    });
});
