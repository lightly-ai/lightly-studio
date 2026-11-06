import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import SmartSelectOverlay from './SmartSelectOverlay.svelte';

const mocks = vi.hoisted(() => ({
    smartSelect: {
        points: [] as { x: number; y: number; positive: boolean }[],
        preview: null as AnnotationPreview | null,
        canSave: false,
        isSaving: false,
        isPending: false,
        box: null,
        isSaving: false,
        addPoint: vi.fn(),
        selectBox: vi.fn(),
        clear: vi.fn(),
        save: vi.fn()
    }
}));

const defaultProps = {
    sample: { width: 100, height: 100 },
    scale: 1,
    isPanning: false,
    saveAs: 'mask' as const,
    smartSelect: mocks.smartSelect
};

const renderOverlay = (props = {}) => {
    const { container } = render(SmartSelectOverlay, { props: { ...defaultProps, ...props } });
    const rect = container.querySelector('rect[role="button"]');
    if (!rect) throw new Error('Missing interaction rect');
    return rect;
};

describe('SmartSelectOverlay', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.smartSelect.points = [];
        mocks.smartSelect.preview = null;
        mocks.smartSelect.canSave = false;
        mocks.smartSelect.isPending = false;
    });

    it('clears the prompts on Escape and keeps the tool open', async () => {
        mocks.smartSelect.points = [{ x: 0.5, y: 0.5, positive: true }];
        const onWindowKeyDown = vi.fn();
        window.addEventListener('keydown', onWindowKeyDown);
        const rect = renderOverlay();

        await fireEvent.keyDown(rect, { key: 'Escape' });

        expect(mocks.smartSelect.clear).toHaveBeenCalledOnce();
        expect(onWindowKeyDown).not.toHaveBeenCalled();
        window.removeEventListener('keydown', onWindowKeyDown);
    });

    it('lets Escape through when there is nothing to clear', async () => {
        const onWindowKeyDown = vi.fn();
        window.addEventListener('keydown', onWindowKeyDown);
        const rect = renderOverlay();

        await fireEvent.keyDown(rect, { key: 'Escape' });

        expect(mocks.smartSelect.clear).not.toHaveBeenCalled();
        expect(onWindowKeyDown).toHaveBeenCalledOnce();
        window.removeEventListener('keydown', onWindowKeyDown);
    });

    it('saves on Enter on the image only', async () => {
        mocks.smartSelect.canSave = true;
        const rect = renderOverlay();

        await fireEvent.keyDown(document.body, { key: 'Enter' });
        expect(mocks.smartSelect.save).not.toHaveBeenCalled();

        await fireEvent.keyDown(rect, { key: 'Enter' });
        expect(mocks.smartSelect.save).toHaveBeenCalledOnce();
    });

    it('lets pointer events through while panning', () => {
        const rect = renderOverlay({ isPanning: true });
        expect(rect).toHaveAttribute('pointer-events', 'none');
    });

    it('blocks pointer events while generating a preview', () => {
        mocks.smartSelect.isPending = true;
        expect(renderOverlay()).toHaveAttribute('pointer-events', 'none');
    });

    it('shows the exclusion cursor while Shift is held and resets on release or blur', async () => {
        const rect = renderOverlay();
        await fireEvent.keyDown(window, { key: 'Shift', shiftKey: true });
        expect(getComputedStyle(rect).cursor).toContain('data:image/svg+xml');
        await fireEvent.keyUp(window, { key: 'Shift', shiftKey: false });
        expect(getComputedStyle(rect).cursor).toBe('crosshair');
        await fireEvent(window, new MouseEvent('pointermove', { shiftKey: true }));
        expect(getComputedStyle(rect).cursor).toContain('data:image/svg+xml');
        await fireEvent.blur(window);
        expect(getComputedStyle(rect).cursor).toBe('crosshair');
    });

    it('marks positive and negative points', () => {
        mocks.smartSelect.points = [
            { x: 0.2, y: 0.2, positive: true },
            { x: 0.8, y: 0.8, positive: false }
        ];
        renderOverlay();
        expect(screen.getByTestId('smart-select-positive-point')).toBeInTheDocument();
        expect(screen.getByTestId('smart-select-negative-point')).toBeInTheDocument();
    });
});
