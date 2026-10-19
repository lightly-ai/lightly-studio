import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import FrameTimeline from './FrameTimeline.svelte';

const createTicks = (timestamps: Array<number | null>): TickView[] =>
    timestamps.map((timestamp_ns, seq_number) => ({ seq_number, timestamp_ns }));

const defaultProps = {
    ticks: createTicks([null, null, null]),
    currentTick: 0,
    isPlaying: false,
    playbackIntervalMs: 100,
    bufferEntireSequence: false,
    onBufferEntireSequenceChange: vi.fn(),
    bufferedRanges: [],
    onPreviousFrame: vi.fn(),
    onNextFrame: vi.fn(),
    onPlayToggle: vi.fn(),
    onPlaybackIntervalChange: vi.fn(),
    onSelectTick: vi.fn()
};

describe('FrameTimeline', () => {
    it('colors tick marks that are included in buffered ranges', () => {
        render(FrameTimeline, {
            props: {
                ...defaultProps,
                bufferedRanges: [{ startIndex: 1, endIndex: 2 }]
            }
        });

        const marks = screen.getAllByTestId('timeline-tick-mark');
        expect(marks[0]).toHaveClass('bg-border');
        expect(marks[1]).toHaveClass('bg-primary');
        expect(marks[2]).toHaveClass('bg-primary');
    });

    it.each([
        { currentTick: 0, label: 'Frame 1 / 3' },
        { currentTick: 1, label: 'Frame 2 / 3' }
    ])(
        'shows the one-based active frame and total tick count ($label)',
        ({ currentTick, label }) => {
            render(FrameTimeline, { props: { ...defaultProps, currentTick } });

            expect(screen.getByText(label)).toBeInTheDocument();
        }
    );

    it('shows an empty frame counter when the sequence has no ticks', () => {
        render(FrameTimeline, { props: { ...defaultProps, ticks: [] } });

        expect(screen.getByText('Frame — / —')).toBeInTheDocument();
    });

    it('toggles complete-sequence buffering from the transport', async () => {
        const onBufferEntireSequenceChange = vi.fn();
        render(FrameTimeline, {
            props: { ...defaultProps, onBufferEntireSequenceChange }
        });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'Buffer entire sequence' }));

        expect(onBufferEntireSequenceChange).toHaveBeenCalledWith(true);
    });

    it('selects ticks with the timeline slider and exposes the playback interval control', async () => {
        const onSelectTick = vi.fn();
        render(FrameTimeline, {
            props: {
                ...defaultProps,
                ticks: createTicks([null, null, null]).map((tick, index) => ({
                    ...tick,
                    seq_number: index * 4
                })),
                currentTick: 0,
                onSelectTick
            }
        });

        const slider = screen.getByRole('slider', { name: 'Frame position' });
        await fireEvent.pointerDown(slider);
        await fireEvent.input(slider, { target: { value: '1' } });
        expect(onSelectTick).not.toHaveBeenCalled();

        await fireEvent.change(slider, {
            target: { value: '2' }
        });
        expect(screen.getByLabelText('Playback speed')).toHaveTextContent('1×');
        expect(screen.getByRole('slider', { name: 'Frame position' })).toHaveAttribute('max', '2');
        expect(onSelectTick).toHaveBeenCalledWith(8);
    });

    it('reports the start and end of slider seeking', async () => {
        const onSeekStart = vi.fn();
        const onSeekEnd = vi.fn();
        render(FrameTimeline, {
            props: { ...defaultProps, onSeekStart, onSeekEnd }
        });

        const slider = screen.getByRole('slider', { name: 'Frame position' });
        await fireEvent.pointerDown(slider);
        await fireEvent.pointerUp(slider);

        expect(onSeekStart).toHaveBeenCalledOnce();
        expect(onSeekEnd).toHaveBeenCalledOnce();
    });

    it('commits the final slider position after dragging', async () => {
        const onSelectTick = vi.fn();
        render(FrameTimeline, {
            props: { ...defaultProps, onSelectTick }
        });

        const slider = screen.getByRole('slider', { name: 'Frame position' });
        await fireEvent.pointerDown(slider);
        await fireEvent.input(slider, { target: { value: '1' } });
        expect(onSelectTick).not.toHaveBeenCalled();

        await fireEvent.change(slider, { target: { value: '2' } });
        expect(onSelectTick).toHaveBeenCalledWith(2);
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

    it('steps between sequences through the exposed handlers', () => {
        const onPreviousSequence = vi.fn();
        const onNextSequence = vi.fn();
        render(FrameTimeline, {
            props: { ...defaultProps, onPreviousSequence, onNextSequence }
        });

        screen.getByRole('button', { name: 'Previous sequence' }).click();
        screen.getByRole('button', { name: 'Next sequence' }).click();

        expect(onPreviousSequence).toHaveBeenCalledOnce();
        expect(onNextSequence).toHaveBeenCalledOnce();
    });

    it('disables sequence stepping when no adjacent sequence handler is given', () => {
        render(FrameTimeline, { props: defaultProps });

        expect(screen.getByRole('button', { name: 'Previous sequence' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Next sequence' })).toBeDisabled();
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
