import { describe, expect, it, vi } from 'vitest';
import { selectCuboid } from './cuboidSelection';

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
