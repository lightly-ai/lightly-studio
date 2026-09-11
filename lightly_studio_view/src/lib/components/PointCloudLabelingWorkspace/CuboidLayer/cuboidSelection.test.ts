import { describe, expect, it, vi } from 'vitest';
import { addCuboidDeleteListeners, selectCuboid } from './cuboidSelection';

describe('selectCuboid', () => {
    it('selects a cuboid only with the select tool active', () => {
        const onselect = vi.fn();

        const selected = selectCuboid({
            annotationId: 'cuboid-1',
            activeTool: 'select',
            onselect
        });
        const ignored = selectCuboid({
            annotationId: 'cuboid-1',
            activeTool: 'rotate',
            onselect
        });

        expect(selected).toBe(true);
        expect(ignored).toBe(false);
        expect(onselect).toHaveBeenCalledTimes(1);
        expect(onselect).toHaveBeenCalledWith('cuboid-1');
    });
});

describe('addCuboidDeleteListeners', () => {
    it('fires oncuboiddelete on Delete key when a cuboid is selected', () => {
        const oncuboiddelete = vi.fn();
        const cleanup = addCuboidDeleteListeners({
            selectedAnnotationId: 'cuboid-1',
            oncuboiddelete
        });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' }));

        expect(oncuboiddelete).toHaveBeenCalledTimes(1);
        expect(oncuboiddelete).toHaveBeenCalledWith('cuboid-1');
        cleanup();
    });

    it('fires oncuboiddelete on Backspace key when a cuboid is selected', () => {
        const oncuboiddelete = vi.fn();
        const cleanup = addCuboidDeleteListeners({
            selectedAnnotationId: 'cuboid-1',
            oncuboiddelete
        });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Backspace' }));

        expect(oncuboiddelete).toHaveBeenCalledTimes(1);
        expect(oncuboiddelete).toHaveBeenCalledWith('cuboid-1');
        cleanup();
    });

    it('does not fire when no cuboid is selected', () => {
        const oncuboiddelete = vi.fn();
        const cleanup = addCuboidDeleteListeners({
            selectedAnnotationId: null,
            oncuboiddelete
        });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' }));

        expect(oncuboiddelete).not.toHaveBeenCalled();
        cleanup();
    });

    it('does not fire on unrelated keys', () => {
        const oncuboiddelete = vi.fn();
        const cleanup = addCuboidDeleteListeners({
            selectedAnnotationId: 'cuboid-1',
            oncuboiddelete
        });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

        expect(oncuboiddelete).not.toHaveBeenCalled();
        cleanup();
    });

    it('stops firing after cleanup', () => {
        const oncuboiddelete = vi.fn();
        const cleanup = addCuboidDeleteListeners({
            selectedAnnotationId: 'cuboid-1',
            oncuboiddelete
        });

        cleanup();
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' }));

        expect(oncuboiddelete).not.toHaveBeenCalled();
    });
});
