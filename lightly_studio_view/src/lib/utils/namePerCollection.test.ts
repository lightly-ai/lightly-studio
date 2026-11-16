import { describe, expect, it } from 'vitest';
import { removeForCollection, renameForCollection } from './namePerCollection';

describe('renameForCollection', () => {
    it('renames the name of the collection only', () => {
        const names = { c1: 'labels', c2: 'labels' };

        expect(renameForCollection(names, 'c1', 'labels', 'gt')).toEqual({
            c1: 'gt',
            c2: 'labels'
        });
        expect(names).toEqual({ c1: 'labels', c2: 'labels' });
    });

    it('keeps another name of the collection', () => {
        expect(renameForCollection({ c1: 'preds' }, 'c1', 'labels', 'gt')).toEqual({ c1: 'preds' });
    });
});

describe('removeForCollection', () => {
    it('removes the name of the collection only', () => {
        expect(removeForCollection({ c1: 'labels', c2: 'labels' }, 'c1', 'labels')).toEqual({
            c2: 'labels'
        });
    });

    it('keeps another name of the collection', () => {
        expect(removeForCollection({ c1: 'preds' }, 'c1', 'labels')).toEqual({ c1: 'preds' });
    });
});
