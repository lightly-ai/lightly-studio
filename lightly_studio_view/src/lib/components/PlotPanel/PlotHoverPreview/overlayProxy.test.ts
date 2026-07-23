import { describe, expect, it, vi } from 'vitest';

import { createOverlayProxyReporter } from './overlayProxy';

describe('createOverlayProxyReporter', () => {
    it('reports the proxy on construct and update, and null on destroy', () => {
        const onProxy = vi.fn();
        const Reporter = createOverlayProxyReporter(onProxy);
        const node = document.createElement('div');
        const proxyA = { location: () => ({ x: 0, y: 0 }), width: 100, height: 100 };
        const proxyB = { ...proxyA, width: 200 };

        const instance = new Reporter(node, { proxy: proxyA });
        expect(onProxy).toHaveBeenLastCalledWith(proxyA);

        instance.update({ proxy: proxyB });
        expect(onProxy).toHaveBeenLastCalledWith(proxyB);

        instance.destroy();
        expect(onProxy).toHaveBeenLastCalledWith(null);
    });
});
