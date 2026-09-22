import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import type { ChannelSummaryView, TickView } from '$lib/api/lightly_studio_local/types.gen';
import FrameTimeline from './FrameTimeline.svelte';

const createChannel = (overrides: Partial<ChannelSummaryView> = {}): ChannelSummaryView => ({
    channel_id: 0,
    group_component_name: 'channel',
    group_component_index: 0,
    ...overrides
});

const createTicks = (timestamps: Array<number | null>): TickView[] =>
    timestamps.map((timestamp_ns, seq_number) => ({ seq_number, timestamp_ns }));

const defaultProps = {
    ticks: createTicks([null, null, null]),
    currentTick: 0,
    isPlaying: false,
    onPreviousFrame: vi.fn(),
    onNextFrame: vi.fn(),
    onPlayToggle: vi.fn()
};

describe('FrameTimeline', () => {
    it('renders placeholder lanes when no channels are given', () => {
        render(FrameTimeline, { props: defaultProps });

        expect(screen.getByTestId('workspace-frame-timeline')).toBeInTheDocument();
        expect(screen.getByText('Track 1')).toBeInTheDocument();
        expect(screen.getByText('Track 2')).toBeInTheDocument();
    });

    it('shows the one-based active frame and total tick count', () => {
        render(FrameTimeline, { props: defaultProps });

        expect(screen.getByText('Frame 1 / 3')).toBeInTheDocument();
    });

    it('shows the one-based position of the current tick', () => {
        render(FrameTimeline, { props: { ...defaultProps, currentTick: 1 } });

        expect(screen.getByText('Frame 2 / 3')).toBeInTheDocument();
    });

    it('renders a lane per lidar and camera channel by name', () => {
        render(FrameTimeline, {
            props: {
                ...defaultProps,
                lidarChannels: [createChannel({ channel_id: 1, group_component_name: 'top' })],
                cameraChannels: [
                    createChannel({ channel_id: 2, group_component_name: 'front' }),
                    createChannel({ channel_id: 3, group_component_name: 'rear' })
                ]
            }
        });

        expect(screen.getByText('top')).toBeInTheDocument();
        expect(screen.getByText('front')).toBeInTheDocument();
        expect(screen.getByText('rear')).toBeInTheDocument();
        expect(screen.queryByText('Track 1')).not.toBeInTheDocument();
    });

    it('uses channels even when only one channel kind is present', () => {
        render(FrameTimeline, {
            props: {
                ...defaultProps,
                lidarChannels: [createChannel({ group_component_name: 'top' })]
            }
        });

        expect(screen.getByText('top')).toBeInTheDocument();
        expect(screen.queryByText('Track 1')).not.toBeInTheDocument();
    });

    it('labels ruler ticks with their timestamp relative to the first tick', () => {
        render(FrameTimeline, {
            props: {
                ...defaultProps,
                ticks: createTicks([1_000_000_000, 1_500_000_000, 2_250_000_000])
            }
        });

        expect(screen.getByTitle('0.00s')).toBeInTheDocument();
        expect(screen.getByTitle('0.50s')).toBeInTheDocument();
        expect(screen.getByTitle('1.25s')).toBeInTheDocument();
    });

    it('leaves ticks unlabelled when no timestamps are indexed yet', () => {
        render(FrameTimeline, { props: { ...defaultProps, ticks: createTicks([null, null]) } });

        expect(screen.queryByTitle(/s$/)).not.toBeInTheDocument();
    });

    it('disables playback when the sequence has no ticks', () => {
        render(FrameTimeline, { props: { ...defaultProps, ticks: [] } });

        expect(screen.getByRole('button', { name: 'Play frames' })).toBeDisabled();
    });

    it('steps between frames and toggles playback through the exposed handlers', () => {
        const onPreviousFrame = vi.fn();
        const onNextFrame = vi.fn();
        const onPlayToggle = vi.fn();
        render(FrameTimeline, {
            props: { ...defaultProps, currentTick: 1, onPreviousFrame, onNextFrame, onPlayToggle }
        });

        screen.getByRole('button', { name: 'Previous frame' }).click();
        screen.getByRole('button', { name: 'Next frame' }).click();
        screen.getByRole('button', { name: 'Play frames' }).click();

        expect(onPreviousFrame).toHaveBeenCalledOnce();
        expect(onNextFrame).toHaveBeenCalledOnce();
        expect(onPlayToggle).toHaveBeenCalledOnce();
    });

    it('shows a pause control while playing', () => {
        render(FrameTimeline, {
            props: { ...defaultProps, isPlaying: true, onPlayToggle: vi.fn() }
        });

        expect(screen.getByRole('button', { name: 'Pause frames' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Play frames' })).not.toBeInTheDocument();
    });

    it('disables stepping past the ends of the sequence', () => {
        const handlers = { onPreviousFrame: vi.fn(), onNextFrame: vi.fn() };
        const { rerender } = render(FrameTimeline, {
            props: { ...defaultProps, currentTick: 0, ...handlers }
        });

        expect(screen.getByRole('button', { name: 'Previous frame' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Next frame' })).toBeEnabled();

        rerender({ ...defaultProps, currentTick: 2, ...handlers });

        expect(screen.getByRole('button', { name: 'Previous frame' })).toBeEnabled();
        expect(screen.getByRole('button', { name: 'Next frame' })).toBeDisabled();
    });
});
