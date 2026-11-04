import { describe, expect, it, vi } from 'vitest';
import { resolveNewBoxClass } from './resolveNewBoxClass';

const bbox = { x: 1, y: 2, width: 30, height: 40 };

describe('resolveNewBoxClass', () => {
    it('uses the sticky class without asking', async () => {
        const requestClass = vi.fn();

        await expect(resolveNewBoxClass({ stickyClass: 'deer', bbox, requestClass })).resolves.toBe(
            'deer'
        );
        expect(requestClass).not.toHaveBeenCalled();
    });

    it('asks at the box with no sticky class', async () => {
        const requestClass = vi.fn().mockResolvedValue('fox');

        await expect(
            resolveNewBoxClass({ stickyClass: undefined, bbox, requestClass })
        ).resolves.toBe('fox');
        expect(requestClass).toHaveBeenCalledWith(bbox);
    });

    it('gives null when the request is cancelled', async () => {
        const requestClass = vi.fn().mockResolvedValue(null);

        await expect(
            resolveNewBoxClass({ stickyClass: undefined, bbox, requestClass })
        ).resolves.toBeNull();
    });
});
