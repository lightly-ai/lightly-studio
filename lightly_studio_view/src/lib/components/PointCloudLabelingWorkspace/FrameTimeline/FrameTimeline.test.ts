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
        expect(screen.getByTestId('timeline-playhead').style.left).toBe('50%');

        await fireEvent.change(slider, {
            target: { value: '2' }
        });
        await fireEvent.pointerUp(slider);
        expect(screen.getByLabelText('Playback speed')).toHaveTextContent('1×');
        expect(screen.getByRole('slider', { name: 'Frame position' })).toHaveAttribute('max', '2');
        expect(onSelectTick).toHaveBeenCalledWith(8);
    });

    it('restores the current-frame marker when seeking is cancelled', async () => {
        const onSelectTick = vi.fn();
        render(FrameTimeline, { props: { ...defaultProps, onSelectTick } });
        const slider = screen.getByRole('slider', { name: 'Frame position' });
        const initialPosition = screen.getByTestId('timeline-playhead').style.left;

        await fireEvent.pointerDown(slider);
        await fireEvent.input(slider, { target: { value: '1' } });
        expect(screen.getByTestId('timeline-playhead').style.left).toBe('50%');
        await fireEvent.pointerCancel(slider);

        expect(onSelectTick).not.toHaveBeenCalled();
        expect(screen.getByTestId('timeline-playhead').style.left).toBe(initialPosition);
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

    it('reports keyboard seeking and commits the selected tick', async () => {
        const onSeekStart = vi.fn();
        const onSeekEnd = vi.fn();
        const onSelectTick = vi.fn();
        render(FrameTimeline, {
            props: { ...defaultProps, onSeekStart, onSeekEnd, onSelectTick }
        });

        const slider = screen.getByRole('slider', { name: 'Frame position' });
        await fireEvent.keyDown(slider, { key: 'ArrowRight' });
        await fireEvent.change(slider, { target: { value: '1' } });
        await fireEvent.keyUp(slider, { key: 'ArrowRight' });

        expect(onSeekStart).toHaveBeenCalledOnce();
        expect(onSeekEnd).toHaveBeenCalledOnce();
        expect(onSelectTick).toHaveBeenCalledWith(1);
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

    describe('zoom', () => {
        const longProps = {
            ...defaultProps,
            ticks: createTicks(Array.from({ length: 100 }, () => null))
        };
        const rulerWidth = () =>
            (screen.getByTestId('timeline-scroll-container').firstElementChild as HTMLElement).style
                .width;

        it('zooms with the buttons and fits all frames again', async () => {
            render(FrameTimeline, { props: longProps });
            expect(rulerWidth()).toBe('100%');
            expect(screen.getByLabelText('Fit timeline')).toBeDisabled();
            expect(screen.getByTestId('timeline-playhead')).toBeInTheDocument();

            await fireEvent.click(screen.getByLabelText('Zoom in timeline'));
            expect(rulerWidth()).toBe('150%');

            await fireEvent.click(screen.getByLabelText('Fit timeline'));
            expect(rulerWidth()).toBe('100%');
        });

        it('zooms with ctrl+wheel but leaves a plain wheel alone', async () => {
            render(FrameTimeline, { props: longProps });
            const timeline = screen.getByTestId('workspace-frame-timeline').lastElementChild!;
            // jsdom has no layout; the wheel handler needs a width to convert pixels to ticks.
            Object.defineProperty(timeline, 'clientWidth', { value: 500 });

            await fireEvent.wheel(timeline, { deltaY: -100 });
            expect(rulerWidth()).toBe('100%');

            await fireEvent.wheel(timeline, { deltaY: -100, ctrlKey: true });
            expect(Number.parseFloat(rulerWidth() ?? '')).toBeGreaterThan(100);
        });

        it('cannot zoom a sequence with fewer than 10 frames', () => {
            render(FrameTimeline, { props: defaultProps });
            expect(screen.getByLabelText('Zoom in timeline')).toBeDisabled();
        });

        it('preserves zoom across frame navigation and playback with refreshed ticks', async () => {
            const { rerender } = render(FrameTimeline, {
                props: { ...longProps, sequenceId: 'sequence-a' }
            });
            await fireEvent.click(screen.getByLabelText('Zoom in timeline'));
            expect(rulerWidth()).toBe('150%');

            for (const [currentTick, isPlaying] of [
                [50, false],
                [51, true],
                [99, false]
            ] as const) {
                await rerender({
                    ...longProps,
                    sequenceId: 'sequence-a',
                    ticks: [...longProps.ticks],
                    currentTick,
                    isPlaying
                });
                expect(rulerWidth()).toBe('150%');
                expect(screen.getByTestId('timeline-playhead').style.left).toBe(
                    `${currentTick + 0.5}%`
                );
            }

            await rerender({ ...longProps, sequenceId: 'sequence-b' });
            expect(rulerWidth()).toBe('100%');
        });

        const manyTicks = {
            ...defaultProps,
            ticks: createTicks(Array.from({ length: 1000 }, () => null))
        };
        const zoomInDeeply = () => {
            const timeline = screen.getByTestId('workspace-frame-timeline').lastElementChild!;
            // jsdom has no layout; the wheel handler needs a width to convert pixels to ticks.
            Object.defineProperty(timeline, 'clientWidth', { value: 500 });
            return fireEvent.wheel(timeline, { deltaY: -1000, ctrlKey: true });
        };

        it('follows the current frame during playback', async () => {
            const { rerender } = render(FrameTimeline, { props: manyTicks });
            await zoomInDeeply();
            // The ruler labels each tick with its one-based number; frame 501 is out of view.
            expect(screen.queryByText('501')).not.toBeInTheDocument();

            await rerender({ ...manyTicks, currentTick: 500, isPlaying: true });
            expect(screen.getByText('501')).toBeInTheDocument();
        });

        it('renders only the marks near the viewport when zoomed in', async () => {
            render(FrameTimeline, { props: manyTicks });
            expect(screen.getAllByTestId('timeline-tick-mark')).toHaveLength(200);

            await zoomInDeeply();
            expect(screen.getAllByTestId('timeline-tick-mark').length).toBeLessThan(100);
        });

        it('puts each ruler label on a long mark at a round frame number', () => {
            render(FrameTimeline, { props: manyTicks });

            const longMarks = screen
                .getAllByTestId('timeline-tick-mark')
                .filter((mark) => mark.hasAttribute('data-labeled'));
            const labels = ['100', '200', '300', '400', '500', '600', '700', '800', '900', '1000'];
            expect(longMarks.map((mark) => mark.style.left)).toEqual(
                labels.map((label) => screen.getByText(label).style.left)
            );
        });

        it('scrolls the timeline in one area with a sticky ruler, toolbar and row labels', () => {
            render(FrameTimeline, {
                props: {
                    ...longProps,
                    showFrameTags: true,
                    onShowFrameTagsChange: vi.fn(),
                    frameTags: [{ tag_id: 'tag-1', name: 'occluded', seq_numbers: [0] }]
                }
            });

            expect(screen.getByTestId('timeline-scroll-container')).toHaveClass('overflow-auto');
            const ruler = screen.getByLabelText('Frame position').closest('.sticky');
            expect(ruler).toHaveClass('top-0');
            expect(screen.getByText('Show frame tags').closest('.sticky')).toHaveClass('right-2');
            expect(screen.getByTestId('tag-row-label')).toHaveClass('sticky', 'left-3');
        });
    });

    it('shows the frame tag rows it receives while frame tags are shown', () => {
        render(FrameTimeline, {
            props: {
                ...defaultProps,
                showFrameTags: true,
                onShowFrameTagsChange: vi.fn(),
                frameTags: [{ tag_id: 'tag-1', name: 'occluded', seq_numbers: [0] }]
            }
        });

        expect(screen.getByTitle('occluded · Frame 1')).toBeInTheDocument();
    });
});
