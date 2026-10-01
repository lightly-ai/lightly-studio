import type { OverlayProxy } from 'embedding-atlas/svelte';

/**
 * Suppresses the embedding view's default JSON-text tooltip. The preview card
 * is rendered by PlotPanel itself so it can control placement (always above
 * the hovered point), which the library's tooltip container does not allow.
 */
export class NoopTooltip {
    update() {}
    destroy() {}
}

/**
 * customOverlay adapter that captures the embedding view's OverlayProxy
 * (data → pixel coordinate conversion) and reports it to the parent.
 */
export function createOverlayProxyReporter(onProxy: (proxy: OverlayProxy | null) => void) {
    return class {
        constructor(_node: HTMLDivElement, props: { proxy: OverlayProxy }) {
            onProxy(props.proxy);
        }

        update(props: { proxy: OverlayProxy }) {
            onProxy(props.proxy);
        }

        destroy() {
            onProxy(null);
        }
    };
}
