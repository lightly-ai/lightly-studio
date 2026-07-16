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
});
