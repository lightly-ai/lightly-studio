import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { createCustomColorStore } from './createCustomColorStore';

describe('createCustomColorStore', () => {
    it('keeps state independent between instances', () => {
        const first = createCustomColorStore();
        const second = createCustomColorStore();

        first.setCustomColor('cat', '#ff0000', 0.5);

        expect(first.getCustomColor('cat')).toEqual({ color: '#ff0000', alpha: 0.5 });
        expect(get(first.colorVersion)).toBe(1);
        expect(second.getCustomColor('cat')).toBeUndefined();
        expect(get(second.customColorsStore)).toEqual({});
        expect(get(second.colorVersion)).toBe(0);
    });
});
