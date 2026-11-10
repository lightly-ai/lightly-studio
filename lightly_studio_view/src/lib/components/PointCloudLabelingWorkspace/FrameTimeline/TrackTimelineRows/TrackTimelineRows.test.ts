import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import TrackTimelineRows from './TrackTimelineRows.svelte';
import type { SequenceTrackView } from '$lib/api/lightly_studio_local/types.gen';

const track = {
    object_track_id: 'track-1',
    object_track_number: 1,
    annotation_source_id: 'source',
    annotation_source_name: 'ground_truth',
    annotation_label_name: 'truck',
    annotations: [0, 1, 3].map((seq_number) => ({
        seq_number,
        annotation_id: `annotation-${seq_number}`,
        annotation_source_id: 'source',
        frame_id: 'odom',
        interpolated: seq_number === 1
    }))
};

const defaultProps = {
    ticks: [0, 1, 2, 3].map((seq_number) => ({ seq_number, timestamp_ns: null })),
    tracks: [track],
    selectedAnnotationId: null,
    onSelectAnnotation: vi.fn(),
    onSelectTick: vi.fn()
};

// jsdom has no PointerEvent, so pointer events are sent as mouse events with a pointer name.
const pointer = (element: HTMLElement, type: string, clientX = 0) =>
    fireEvent(element, new MouseEvent(type, { bubbles: true, clientX }));

describe('TrackTimelineRows', () => {
    it('draws one run per stretch of drawn or interpolated annotations', () => {
        render(TrackTimelineRows, { props: defaultProps });

        expect(screen.getByRole('group', { name: 'Track annotation legend' })).toBeTruthy();
        expect(screen.getByText('Drawn annotation')).toBeTruthy();
        expect(screen.getByText('Interpolated annotation')).toBeTruthy();
        const runs = screen.getAllByTitle(/^Frames? \d/);
        expect(runs.map((run) => run.getAttribute('title'))).toEqual([
            'Frame 1 · drawn',
            'Frame 2 · interpolated',
            'Frame 4 · drawn'
        ]);
    });

    it('selects the annotation of the clicked tick', async () => {
        const onSelectTick = vi.fn();
        const onSelectAnnotation = vi.fn();
        render(TrackTimelineRows, {
            props: { ...defaultProps, onSelectTick, onSelectAnnotation }
        });
        const row = screen.getByLabelText('Select truck track 1 position');
        vi.spyOn(row, 'getBoundingClientRect').mockReturnValue({
            left: 0,
            width: 400
        } as DOMRect);

        await fireEvent.click(row, { clientX: 350 });

        expect(onSelectTick).toHaveBeenCalledWith(3);
        expect(onSelectAnnotation).toHaveBeenCalledWith('annotation-3');
    });

    it('offers to start a track only when a cuboid can start one, even without tracks', async () => {
        const onStartTrack = vi.fn();
        const { rerender } = render(TrackTimelineRows, {
            props: { ...defaultProps, tracks: [] }
        });
        expect(screen.queryByText('Start track from selected cuboid')).toBeNull();

        await rerender({ ...defaultProps, tracks: [], onStartTrack });
        await fireEvent.click(screen.getByText('Start track from selected cuboid'));

        expect(onStartTrack).toHaveBeenCalledOnce();
    });

    it('offers to add a track while editing and shows a hint once armed', async () => {
        const onAddTrack = vi.fn();
        const { rerender } = render(TrackTimelineRows, {
            props: { ...defaultProps, tracks: [] }
        });
        expect(screen.queryByText('Add object track')).toBeNull();

        await rerender({ ...defaultProps, tracks: [], onAddTrack });
        await fireEvent.click(screen.getByText('Add object track'));
        expect(onAddTrack).toHaveBeenCalledOnce();
        expect(screen.queryByText(/place the first cuboid/)).toBeNull();

        await rerender({ ...defaultProps, tracks: [], onAddTrack, isAddingTrack: true });
        expect(screen.getByText('Cancel')).toBeTruthy();
        expect(screen.getByText(/place the first cuboid/)).toBeTruthy();
    });

    describe('extending a track', () => {
        const wideTrack = {
            ...track,
            annotations: [2, 3].map((seq_number) => ({
                seq_number,
                annotation_id: `annotation-${seq_number}`,
                annotation_source_id: 'source',
                frame_id: 'odom',
                interpolated: false
            }))
        };
        const props = {
            ...defaultProps,
            ticks: [0, 1, 2, 3, 4, 5].map((seq_number) => ({ seq_number, timestamp_ns: null })),
            tracks: [wideTrack]
        };

        const mockBar = (container: HTMLElement) => {
            const bar = container.querySelector('[data-track-id] .relative') as HTMLElement;
            vi.spyOn(bar, 'getBoundingClientRect').mockReturnValue({
                left: 0,
                width: 600
            } as DOMRect);
        };

        it('shows no handles unless extending is enabled', () => {
            render(TrackTimelineRows, { props });
            expect(screen.queryByTestId('track-extend-end')).toBeNull();
        });

        it('previews and commits an outward drag of the end handle', async () => {
            const onExtendTrack = vi.fn();
            const onExtendStart = vi.fn();
            const onExtendEnd = vi.fn();
            const { container } = render(TrackTimelineRows, {
                props: { ...props, onExtendTrack, onExtendStart, onExtendEnd }
            });
            mockBar(container);
            const handle = screen.getByTestId('track-extend-end');

            await pointer(handle, 'pointerdown', 400);
            await pointer(handle, 'pointermove', 590);
            expect(screen.getByTestId('track-extend-preview')).toBeTruthy();
            expect(screen.getByRole('tooltip')).toHaveTextContent('Ticks 3–6');
            expect(handle).toHaveStyle({ left: '100%' });
            await pointer(handle, 'pointerup');

            expect(onExtendStart).toHaveBeenCalledOnce();
            expect(onExtendEnd).toHaveBeenCalledOnce();
            expect(onExtendTrack).toHaveBeenCalledWith(wideTrack, 2, 5);
            expect(screen.queryByTestId('track-extend-preview')).toBeNull();
            expect(screen.queryByRole('tooltip')).toBeNull();
        });

        it('commits nothing when the handle is dragged back inside the track', async () => {
            const onExtendTrack = vi.fn();
            const { container } = render(TrackTimelineRows, {
                props: { ...props, onExtendTrack }
            });
            mockBar(container);
            const handle = screen.getByTestId('track-extend-start');

            await pointer(handle, 'pointerdown', 200);
            await pointer(handle, 'pointermove', 450);
            await pointer(handle, 'pointerup');

            expect(onExtendTrack).not.toHaveBeenCalled();
        });

        it('cancels the drag without committing', async () => {
            const onExtendTrack = vi.fn();
            const onExtendEnd = vi.fn();
            const { container } = render(TrackTimelineRows, {
                props: { ...props, onExtendTrack, onExtendEnd }
            });
            mockBar(container);
            const handle = screen.getByTestId('track-extend-end');

            await pointer(handle, 'pointerdown', 400);
            await pointer(handle, 'pointermove', 590);
            await pointer(handle, 'pointercancel');

            expect(onExtendTrack).not.toHaveBeenCalled();
            expect(onExtendEnd).toHaveBeenCalledOnce();
        });
    });

    describe('deleting a track', () => {
        it('shows no close button unless deleting is enabled', () => {
            render(TrackTimelineRows, { props: defaultProps });
            expect(screen.queryByLabelText('Delete truck track 1')).toBeNull();
        });

        it('asks for confirmation with the cuboid count before deleting', async () => {
            const onDeleteTrack = vi.fn().mockResolvedValue(undefined);
            render(TrackTimelineRows, { props: { ...defaultProps, onDeleteTrack } });

            await fireEvent.click(screen.getByLabelText('Delete truck track 1'));
            expect(onDeleteTrack).not.toHaveBeenCalled();
            expect(screen.getByText('3 cuboids')).toBeTruthy();

            await fireEvent.click(screen.getByText('Delete track and 3 cuboids'));

            expect(onDeleteTrack).toHaveBeenCalledWith(track);
        });

        it('does not delete when the dialog is cancelled', async () => {
            const onDeleteTrack = vi.fn();
            render(TrackTimelineRows, { props: { ...defaultProps, onDeleteTrack } });

            await fireEvent.click(screen.getByLabelText('Delete truck track 1'));
            await fireEvent.click(screen.getByText('Cancel'));

            expect(onDeleteTrack).not.toHaveBeenCalled();
        });
    });

    describe('with many tracks', () => {
        const manyTracks: SequenceTrackView[] = Array.from({ length: 14 }, (_, index) => ({
            ...track,
            object_track_id: `track-${index + 1}`,
            object_track_number: index + 1
        }));
        const props = { ...defaultProps, tracks: manyTracks, sequenceId: 'sequence-1' };

        it('lists the first ten tracks and says how many are shown', () => {
            localStorage.clear();
            const { container } = render(TrackTimelineRows, { props });

            expect(container.querySelectorAll('[data-track-id]')).toHaveLength(10);
            expect(screen.getByText(/Showing 10 of 14 tracks/)).toBeTruthy();
        });

        it('does not list the track of the selected annotation when it is not chosen', () => {
            localStorage.clear();
            localStorage.setItem(
                'lightlyStudio_trackTimelineVisibleTracks_sequence-1',
                JSON.stringify(
                    manyTracks.slice(0, 10).map((item) => `${item.object_track_id}-source`)
                )
            );
            const { container } = render(TrackTimelineRows, {
                props: {
                    ...props,
                    tracks: manyTracks.map((item) => ({
                        ...item,
                        annotations: item.annotations.map((annotation) => ({
                            ...annotation,
                            annotation_id: `${item.object_track_id}-${annotation.annotation_id}`
                        }))
                    })),
                    selectedAnnotationId: 'track-14-annotation-0'
                }
            });

            expect(container.querySelectorAll('[data-track-id]')).toHaveLength(10);
            expect(container.querySelector('[data-track-id="track-14"]')).toBeNull();
        });

        it('shows only the stored tracks for this sequence', () => {
            localStorage.setItem(
                'lightlyStudio_trackTimelineVisibleTracks_sequence-1',
                JSON.stringify(['track-12-source', 'track-13-source'])
            );
            const { container } = render(TrackTimelineRows, { props });

            expect(
                [...container.querySelectorAll('[data-track-id]')].map((row) =>
                    row.getAttribute('data-track-id')
                )
            ).toEqual(['track-12', 'track-13']);
            expect(screen.getByText(/Showing 2 of 14 tracks/)).toBeTruthy();
            localStorage.clear();
        });

        it('keeps a newly added track listed', async () => {
            localStorage.clear();
            const { container, rerender } = render(TrackTimelineRows, { props });

            await rerender({
                ...props,
                tracks: [
                    ...manyTracks,
                    { ...track, object_track_id: 'track-15', object_track_number: 15 }
                ]
            });

            expect(container.querySelector('[data-track-id="track-15"]')).toBeTruthy();
            expect(container.querySelectorAll('[data-track-id]')).toHaveLength(11);
        });
    });
});
