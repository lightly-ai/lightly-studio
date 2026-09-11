import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import FrameTimelineRuler from './FrameTimelineRuler.svelte';

function rect(): DOMRect {
    return {
        left: 0,
        width: 200,
        top: 0,
        height: 16,
        right: 200,
        bottom: 16,
        x: 0,
        y: 0,
        toJSON: () => ({})
    } as DOMRect;
}

describe('FrameTimelineRuler', () => {
    it('reports the scrubbed position on click, scaled to the frame range', () => {
        const onScrub = vi.fn();
        render(FrameTimelineRuler, { props: { frameCount: 5, position: 0, onScrub } });

        const ruler = screen.getByTestId('workspace-frame-ruler');
        vi.spyOn(ruler, 'getBoundingClientRect').mockReturnValue(rect());
        ruler.setPointerCapture = vi.fn();

        // 200px wide over 5 frames (0..4) → 50px/frame; clicking at 120px lands on frame 2.
        ruler.dispatchEvent(new MouseEvent('pointerdown', { clientX: 120, bubbles: true }));

        expect(onScrub).toHaveBeenCalledWith(2);
    });

    it('continues reporting positions while dragging', () => {
        const onScrub = vi.fn();
        render(FrameTimelineRuler, { props: { frameCount: 5, position: 0, onScrub } });

        const ruler = screen.getByTestId('workspace-frame-ruler');
        vi.spyOn(ruler, 'getBoundingClientRect').mockReturnValue(rect());
        ruler.setPointerCapture = vi.fn();

        ruler.dispatchEvent(new MouseEvent('pointerdown', { clientX: 0, bubbles: true }));
        ruler.dispatchEvent(new MouseEvent('pointermove', { clientX: 200, bubbles: true }));

        expect(onScrub).toHaveBeenNthCalledWith(1, 0);
        expect(onScrub).toHaveBeenNthCalledWith(2, 4);
    });

    it('steps one frame per arrow key', async () => {
        const onScrub = vi.fn();
        render(FrameTimelineRuler, { props: { frameCount: 5, position: 2, onScrub } });

        const ruler = screen.getByTestId('workspace-frame-ruler');
        ruler.focus();
        await ruler.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
        await ruler.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));

        expect(onScrub).toHaveBeenNthCalledWith(1, 3);
        expect(onScrub).toHaveBeenNthCalledWith(2, 1);
    });

    it('never scrubs while disabled', () => {
        const onScrub = vi.fn();
        render(FrameTimelineRuler, {
            props: { frameCount: 5, position: 0, disabled: true, onScrub }
        });

        const ruler = screen.getByTestId('workspace-frame-ruler');
        expect(ruler).toHaveAttribute('aria-disabled', 'true');
        expect(ruler).toHaveAttribute('tabindex', '-1');

        vi.spyOn(ruler, 'getBoundingClientRect').mockReturnValue(rect());
        ruler.dispatchEvent(new MouseEvent('pointerdown', { clientX: 120, bubbles: true }));

        expect(onScrub).not.toHaveBeenCalled();
    });
});
