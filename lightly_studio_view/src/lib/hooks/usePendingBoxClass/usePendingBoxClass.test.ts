import { afterEach, describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { usePendingBoxClass } from './usePendingBoxClass';

const first = { x: 1, y: 2, width: 30, height: 40 };
const second = { x: 50, y: 60, width: 10, height: 20 };

describe('usePendingBoxClass', () => {
    afterEach(() => {
        usePendingBoxClass().cancel();
    });

    it('resolves the picked class and clears the request', async () => {
        const { request, requestClass, resolve } = usePendingBoxClass();

        const result = requestClass(first);
        expect(get(request)).toEqual({ bbox: first });
        resolve('deer');

        await expect(result).resolves.toBe('deer');
        expect(get(request)).toBeNull();
    });

    it('resolves null on cancel', async () => {
        const { request, requestClass, cancel } = usePendingBoxClass();

        const result = requestClass(first);
        cancel();

        await expect(result).resolves.toBeNull();
        expect(get(request)).toBeNull();
    });

    it('drops the first box when a second one asks for a class', async () => {
        const { request, requestClass, resolve } = usePendingBoxClass();

        const firstResult = requestClass(first);
        const secondResult = requestClass(second);
        expect(get(request)).toEqual({ bbox: second });
        resolve('fox');

        await expect(firstResult).resolves.toBeNull();
        await expect(secondResult).resolves.toBe('fox');
    });

    it('shares the request between callers', () => {
        usePendingBoxClass().requestClass(first);

        expect(get(usePendingBoxClass().request)).toEqual({ bbox: first });
    });

    it('ignores resolve and cancel with nothing pending', () => {
        const { request, resolve, cancel } = usePendingBoxClass();

        expect(() => resolve('x')).not.toThrow();
        expect(() => cancel()).not.toThrow();
        expect(get(request)).toBeNull();
    });
});
