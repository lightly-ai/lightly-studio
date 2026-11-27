import { describe, expect, it, vi } from 'vitest';
import { createCuboidHoverTracker } from './cuboidHoverTracker';

describe('createCuboidHoverTracker', () => {
    it('highlights the only hovered cuboid', () => {
        const onhover = vi.fn();
        const tracker = createCuboidHoverTracker(onhover);

        tracker.enter('cuboid-a', 100);

        expect(onhover).toHaveBeenCalledWith('cuboid-a', null);
    });

    it('highlights the smallest cuboid when multiple are hovered', () => {
        const onhover = vi.fn();
        const tracker = createCuboidHoverTracker(onhover);

        tracker.enter('outer', 500);
        tracker.enter('inner', 10);

        expect(onhover).toHaveBeenLastCalledWith('inner', null);
    });

    it('falls back to the remaining cuboid after one leaves', () => {
        const onhover = vi.fn();
        const tracker = createCuboidHoverTracker(onhover);

        tracker.enter('outer', 500);
        tracker.enter('inner', 10);
        tracker.leave('inner');

        expect(onhover).toHaveBeenLastCalledWith('outer', null);
    });

    it('reports null when the last cuboid leaves', () => {
        const onhover = vi.fn();
        const tracker = createCuboidHoverTracker(onhover);

        tracker.enter('cuboid-a', 100);
        tracker.leave('cuboid-a');

        expect(onhover).toHaveBeenLastCalledWith(null, null);
    });

    it('clears all tracked cuboids', () => {
        const onhover = vi.fn();
        const tracker = createCuboidHoverTracker(onhover);

        tracker.enter('a', 10);
        tracker.enter('b', 20);
        onhover.mockClear();
        tracker.clear();

        expect(onhover).not.toHaveBeenCalled();
    });

    describe('handleSelectionHover', () => {
        it('clears hovered cuboids and emits null when called with null', () => {
            const onhover = vi.fn();
            const tracker = createCuboidHoverTracker(onhover);
            tracker.enter('a', 10);
            onhover.mockClear();

            tracker.handleSelectionHover(null);

            expect(onhover).toHaveBeenCalledExactlyOnceWith(null, null);
        });

        it('forwards a non-null annotation id through onhover', () => {
            const onhover = vi.fn();
            const tracker = createCuboidHoverTracker(onhover);

            tracker.handleSelectionHover('cuboid-a');

            expect(onhover).toHaveBeenCalledWith('cuboid-a', null);
        });
    });

    describe('clickState', () => {
        it('starts not clicked', () => {
            const tracker = createCuboidHoverTracker(() => {});

            expect(tracker.isClicked()).toBe(false);
        });

        it('marks clicked via markClicked', () => {
            const tracker = createCuboidHoverTracker(() => {});

            tracker.markClicked();

            expect(tracker.isClicked()).toBe(true);
        });

        it('marks clicked when hit is called', () => {
            const tracker = createCuboidHoverTracker(() => {});

            tracker.hit('a', 10, () => {});

            expect(tracker.isClicked()).toBe(true);
        });

        it('resets clicked state', () => {
            const tracker = createCuboidHoverTracker(() => {});
            tracker.markClicked();

            tracker.resetClicked();

            expect(tracker.isClicked()).toBe(false);
        });
    });

    describe('onCuboidHit', () => {
        it('picks the smallest cuboid when multiple are hit in the same microtask', async () => {
            const onselect = vi.fn();
            const tracker = createCuboidHoverTracker(() => {});

            tracker.hit('outer', 500, onselect);
            tracker.hit('inner', 10, onselect);
            await Promise.resolve();

            expect(onselect).toHaveBeenCalledExactlyOnceWith('inner');
        });

        it('does not call onselect when no hits are registered', async () => {
            const onselect = vi.fn();
            createCuboidHoverTracker(() => {});

            await Promise.resolve();

            expect(onselect).not.toHaveBeenCalled();
        });

        it('resets pending hits after resolving so subsequent clicks are independent', async () => {
            const onselect = vi.fn();
            const tracker = createCuboidHoverTracker(() => {});

            tracker.hit('first', 100, onselect);
            await Promise.resolve();
            onselect.mockClear();

            tracker.hit('second', 200, onselect);
            await Promise.resolve();

            expect(onselect).toHaveBeenCalledExactlyOnceWith('second');
        });
    });
});
