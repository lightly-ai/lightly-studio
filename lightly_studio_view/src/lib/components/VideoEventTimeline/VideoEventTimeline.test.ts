import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import VideoEventTimeline from './VideoEventTimeline.svelte';
import type { VideoEvent } from '$lib/utils';

function makeEvent(overrides: Partial<VideoEvent>): VideoEvent {
    return {
        id: 'e',
        annotationCollectionId: 'coll-1',
        label: 'Jump',
        startTimeS: 0,
        endTimeS: 2,
        color: 'rgba(10, 20, 30, 0.7)',
        contrastColor: 'rgba(245, 235, 225, 0.7)',
        ...overrides
    };
}

describe('VideoEventTimeline', () => {
    it('renders a bar per event', () => {
        const { getAllByRole } = render(VideoEventTimeline, {
            props: {
                events: [
                    makeEvent({ id: 'a', label: 'A' }),
                    makeEvent({ id: 'b', label: 'B', startTimeS: 3, endTimeS: 5 })
                ],
                durationS: 10
            }
        });

        expect(getAllByRole('button')).toHaveLength(2);
    });

    it('positions bars by start and end time', () => {
        const { getByText } = render(VideoEventTimeline, {
            props: {
                events: [makeEvent({ id: 'a', label: 'Mid', startTimeS: 2, endTimeS: 4 })],
                durationS: 10
            }
        });

        const barContainer = getByText('Mid').closest('button')?.parentElement as HTMLElement;
        expect(barContainer.style.left).toBe('20%');
        expect(barContainer.style.width).toBe('20%');
    });

    it('calls onSeek with the event start time when clicked', async () => {
        const onSeek = vi.fn();
        const { getByText } = render(VideoEventTimeline, {
            props: {
                events: [makeEvent({ id: 'a', label: 'Clip', startTimeS: 7, endTimeS: 9 })],
                durationS: 10,
                onSeek
            }
        });

        await fireEvent.click(getByText('Clip'));
        expect(onSeek).toHaveBeenCalledWith(7);
    });

    it('shows a placeholder when there are no events', () => {
        const { getByText, queryAllByRole } = render(VideoEventTimeline, {
            props: { events: [], durationS: 10 }
        });

        expect(getByText('No events for this video.')).toBeTruthy();
        expect(queryAllByRole('button')).toHaveLength(0);
    });

    it('hides the header when showHeader is false', () => {
        const { queryByText } = render(VideoEventTimeline, {
            props: {
                events: [makeEvent({ id: 'a' })],
                durationS: 10,
                title: 'Events',
                showHeader: false
            }
        });

        expect(queryByText('Events')).toBeFalsy();
    });

    it('renders drag handles only when editable', () => {
        const { queryAllByRole, rerender } = render(VideoEventTimeline, {
            props: { events: [makeEvent({ id: 'a' })], durationS: 10 }
        });
        expect(queryAllByRole('slider')).toHaveLength(0);

        rerender({ events: [makeEvent({ id: 'a' })], durationS: 10, editable: true });
        // A start and an end handle per event.
        expect(queryAllByRole('slider')).toHaveLength(2);
    });

    it('reports a new span after dragging an edge handle', () => {
        const onResize = vi.fn();
        const onSeek = vi.fn();
        const event = makeEvent({ id: 'a', startTimeS: 4, endTimeS: 8 });
        const { getByRole, getAllByRole } = render(VideoEventTimeline, {
            props: { events: [event], durationS: 20, editable: true, onResize, onSeek }
        });

        // 200px-wide track over a 20s video → 10px per second.
        vi.spyOn(getByRole('group'), 'getBoundingClientRect').mockReturnValue({
            left: 0,
            width: 200,
            top: 0,
            height: 22,
            right: 200,
            bottom: 22,
            x: 0,
            y: 0,
            toJSON: () => ({})
        } as DOMRect);

        const startHandle = getAllByRole('slider')[0];
        startHandle.setPointerCapture = vi.fn();
        startHandle.releasePointerCapture = vi.fn();

        // jsdom drops clientX on synthetic PointerEvents, so use MouseEvent.
        startHandle.dispatchEvent(new MouseEvent('pointerdown', { clientX: 40, bubbles: true }));
        startHandle.dispatchEvent(new MouseEvent('pointermove', { clientX: 20, bubbles: true }));
        startHandle.dispatchEvent(new MouseEvent('pointerup', { clientX: 20, bubbles: true }));

        // Dragged start handle to 20px → 2s; end stays at 8s.
        expect(onResize).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }), 2, 8);
        // Playback follows the dragged edge so the frame at 2s is visible.
        expect(onSeek).toHaveBeenLastCalledWith(2);
    });

    it('shows the add button only when editable with an onAddEvent handler', () => {
        const { queryByTestId, rerender } = render(VideoEventTimeline, {
            props: { events: [], durationS: 20, editable: false, onAddEvent: vi.fn() }
        });
        expect(queryByTestId('add-event-button')).toBeFalsy();

        rerender({ events: [], durationS: 20, editable: true, onAddEvent: vi.fn() });
        expect(queryByTestId('add-event-button')).toBeTruthy();
    });

    it('adds an event spanning from the current time with a default length', async () => {
        const onAddEvent = vi.fn();
        const { getByTestId } = render(VideoEventTimeline, {
            props: { events: [], durationS: 20, currentTimeS: 3, editable: true, onAddEvent }
        });

        await fireEvent.click(getByTestId('add-event-button'));
        // Default 1s span starting at the playhead (3s).
        expect(onAddEvent).toHaveBeenCalledWith(3, 4);
    });

    it('clamps a new event that would overflow the end of the video', async () => {
        const onAddEvent = vi.fn();
        const { getByTestId } = render(VideoEventTimeline, {
            props: { events: [], durationS: 10, currentTimeS: 10, editable: true, onAddEvent }
        });

        await fireEvent.click(getByTestId('add-event-button'));
        // A 1s span can't start at 10s in a 10s video, so it is shifted back to end at 10s.
        expect(onAddEvent).toHaveBeenCalledWith(9, 10);
    });

    it('shows the delete button only when editable with an onDelete handler', () => {
        const { queryByTestId, rerender } = render(VideoEventTimeline, {
            props: { events: [makeEvent({ id: 'a' })], durationS: 10, onDelete: vi.fn() }
        });
        expect(queryByTestId('delete-event-button')).toBeFalsy();

        rerender({
            events: [makeEvent({ id: 'a' })],
            durationS: 10,
            editable: true,
            onDelete: vi.fn()
        });
        expect(queryByTestId('delete-event-button')).toBeTruthy();
    });

    it('calls onDelete without seeking when the trash button is clicked', async () => {
        const onDelete = vi.fn();
        const onSeek = vi.fn();
        const event = makeEvent({ id: 'a', label: 'Clip' });
        const { getByTestId } = render(VideoEventTimeline, {
            props: { events: [event], durationS: 10, editable: true, onDelete, onSeek }
        });

        await fireEvent.click(getByTestId('delete-event-button'));
        expect(onDelete).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }));
        // The bar's seek click must not fire when deleting.
        expect(onSeek).not.toHaveBeenCalled();
    });
});
