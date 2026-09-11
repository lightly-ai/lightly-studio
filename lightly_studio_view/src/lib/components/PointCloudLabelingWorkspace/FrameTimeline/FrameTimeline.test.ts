import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import FrameTimeline from './FrameTimeline.svelte';
import type { FrameNavigation, TimelineTrack } from '../types';

function navigation(overrides: Partial<FrameNavigation> = {}): FrameNavigation {
    return {
        position: 1,
        frameCount: 3,
        hasMore: true,
        isLoading: false,
        previous: vi.fn(),
        next: vi.fn(),
        seek: vi.fn(),
        ...overrides
    };
}

function track(overrides: Partial<TimelineTrack> = {}): TimelineTrack {
    return {
        id: 'track-0',
        label: 'Vehicle',
        keyframes: [{ id: 'keyframe-0', framePosition: 0 }],
        presentFramePositions: [0],
        ...overrides
    };
}

describe('FrameTimeline', () => {
    it('leaves its controls disabled without navigation', () => {
        render(FrameTimeline);

        expect(screen.getByTestId('workspace-frame-position')).toHaveTextContent('Frame — / —');
        expect(screen.getByLabelText('Previous frame')).toBeDisabled();
        expect(screen.getByLabelText('Next frame')).toBeDisabled();
        expect(screen.getByLabelText('Play frames')).toBeDisabled();
        expect(screen.getByTestId('workspace-frame-ruler')).toHaveAttribute(
            'aria-disabled',
            'true'
        );
    });

    it('reports the position, and that more frames follow', () => {
        render(FrameTimeline, { props: { navigation: navigation() } });

        expect(screen.getByTestId('workspace-frame-position')).toHaveTextContent('Frame 2 / 3+');
    });

    it('steps backwards and forwards', async () => {
        const nav = navigation();
        render(FrameTimeline, { props: { navigation: nav } });

        await userEvent.click(screen.getByLabelText('Previous frame'));
        await userEvent.click(screen.getByLabelText('Next frame'));

        expect(nav.previous).toHaveBeenCalledOnce();
        expect(nav.next).toHaveBeenCalledOnce();
    });

    it('shows that a frame is being read', () => {
        render(FrameTimeline, { props: { navigation: navigation({ isLoading: true }) } });

        expect(screen.getByText('loading…')).toBeInTheDocument();
    });

    it('enables the ruler once navigation exposes seek', () => {
        render(FrameTimeline, { props: { navigation: navigation() } });

        expect(screen.getByTestId('workspace-frame-ruler')).toHaveAttribute(
            'aria-disabled',
            'false'
        );
    });

    it('shows a message instead of lanes when there are no tracks', () => {
        render(FrameTimeline, { props: { navigation: navigation() } });

        expect(screen.getByText('No object tracks for this frame range.')).toBeInTheDocument();
    });

    it('renders one lane per track and forwards selection', async () => {
        const onSelectTrack = vi.fn();
        render(FrameTimeline, {
            props: { navigation: navigation(), tracks: [track()], onSelectTrack }
        });

        expect(screen.getAllByTestId('workspace-timeline-track')).toHaveLength(1);
        await userEvent.click(screen.getByRole('button', { name: 'Vehicle' }));

        expect(onSelectTrack).toHaveBeenCalledWith('track-0');
    });

    it('blocks a step when the navigation guard declines', async () => {
        const nav = navigation();
        const guardNavigation = vi.fn().mockResolvedValue(false);
        render(FrameTimeline, { props: { navigation: nav, guardNavigation } });

        await userEvent.click(screen.getByLabelText('Next frame'));
        await waitFor(() => expect(guardNavigation).toHaveBeenCalledOnce());

        expect(nav.next).not.toHaveBeenCalled();
    });

    it('allows the step once the navigation guard approves', async () => {
        const nav = navigation();
        const guardNavigation = vi.fn().mockResolvedValue(true);
        render(FrameTimeline, { props: { navigation: nav, guardNavigation } });

        await userEvent.click(screen.getByLabelText('Next frame'));

        await waitFor(() => expect(nav.next).toHaveBeenCalledOnce());
    });

    describe('playback', () => {
        beforeEach(() => vi.useFakeTimers());
        afterEach(() => vi.useRealTimers());

        it('steps forward on an interval while playing', async () => {
            const nav = navigation();
            render(FrameTimeline, { props: { navigation: nav } });

            await userEvent.setup({ delay: null }).click(screen.getByLabelText('Play frames'));
            expect(screen.getByLabelText('Pause playback')).toBeInTheDocument();

            await vi.advanceTimersByTimeAsync(200);
            await vi.advanceTimersByTimeAsync(200);

            expect(nav.next).toHaveBeenCalledTimes(2);
        });

        it('cannot start playback once already at the last known frame', () => {
            const nav = navigation({ position: 2, frameCount: 3, hasMore: false });
            render(FrameTimeline, { props: { navigation: nav } });

            expect(screen.getByLabelText('Play frames')).toBeDisabled();
        });

        it('skips a tick rather than piling up calls while a frame is loading', async () => {
            const nav = navigation({ isLoading: true });
            render(FrameTimeline, { props: { navigation: nav } });

            await userEvent.setup({ delay: null }).click(screen.getByLabelText('Play frames'));
            await vi.advanceTimersByTimeAsync(600);

            expect(nav.next).not.toHaveBeenCalled();
        });

        it('pauses on request', async () => {
            const nav = navigation();
            render(FrameTimeline, { props: { navigation: nav } });

            const user = userEvent.setup({ delay: null });
            await user.click(screen.getByLabelText('Play frames'));
            await user.click(screen.getByLabelText('Pause playback'));
            await vi.advanceTimersByTimeAsync(600);

            expect(nav.next).not.toHaveBeenCalled();
        });
    });
});
