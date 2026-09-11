import { describe, expect, it, vi } from 'vitest';
import { createCameraImageStore } from './cameraImageStore';

function bitmap() {
    return { close: vi.fn() } as unknown as ImageBitmap;
}

describe('createCameraImageStore', () => {
    it('hands back the picture a frame refers to', () => {
        const store = createCameraImageStore(2);
        const front = bitmap();

        store.add('frame-0', [{ resourceId: 'cam:1', bitmap: front }]);

        expect(store.get('cam:1')).toBe(front);
        expect(store.get('cam:absent')).toBeUndefined();
    });

    it('closes the pictures of frames that fall out of the window', () => {
        const store = createCameraImageStore(2);
        const oldest = bitmap();
        store.add('frame-0', [{ resourceId: 'a', bitmap: oldest }]);
        store.add('frame-1', [{ resourceId: 'b', bitmap: bitmap() }]);

        store.add('frame-2', [{ resourceId: 'c', bitmap: bitmap() }]);

        expect(oldest.close).toHaveBeenCalledOnce();
        expect(store.get('a')).toBeUndefined();
        expect(store.get('c')).toBeDefined();
        expect(store.size).toBe(2);
    });

    it('replaces a frame it already holds rather than keeping both', () => {
        const store = createCameraImageStore(2);
        const replaced = bitmap();
        store.add('frame-0', [{ resourceId: 'a', bitmap: replaced }]);

        store.add('frame-0', [{ resourceId: 'a', bitmap: bitmap() }]);

        expect(replaced.close).toHaveBeenCalledOnce();
        expect(store.size).toBe(1);
    });

    it('closes everything it holds when cleared', () => {
        const store = createCameraImageStore(4);
        const held = bitmap();
        store.add('frame-0', [{ resourceId: 'a', bitmap: held }]);

        store.clear();

        expect(held.close).toHaveBeenCalledOnce();
        expect(store.size).toBe(0);
    });
});
