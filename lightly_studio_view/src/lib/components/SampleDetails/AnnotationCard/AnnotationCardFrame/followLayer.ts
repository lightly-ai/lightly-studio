/**
 * Calls `onChange` once per frame after anything that moves `layer` on screen changes: a pan or
 * zoom transform or a viewBox between the layer and its canvas, or the size of the canvas or of
 * `panel`. Returns the cleanup.
 */
export const followLayer = (
    layer: SVGGraphicsElement,
    panel: HTMLElement,
    onChange: () => void
): (() => void) => {
    let frame = 0;
    const schedule = () => {
        if (frame) return;
        frame = requestAnimationFrame(() => {
            frame = 0;
            onChange();
        });
    };
    const canvas = layer.ownerSVGElement;
    const mutations = new MutationObserver(schedule);
    for (
        let node: Element | null = layer;
        node;
        node = node === canvas ? null : node.parentElement
    ) {
        mutations.observe(node, { attributes: true, attributeFilter: ['transform', 'viewBox'] });
    }
    const resizes = new ResizeObserver(schedule);
    resizes.observe(panel);
    if (canvas) resizes.observe(canvas);
    window.addEventListener('resize', schedule);
    window.addEventListener('scroll', schedule, true);
    schedule();
    return () => {
        cancelAnimationFrame(frame);
        mutations.disconnect();
        resizes.disconnect();
        window.removeEventListener('resize', schedule);
        window.removeEventListener('scroll', schedule, true);
    };
};
