/**
 * Svelte action that adds scroll-to-zoom and drag-to-pan to a container.
 * The transform is applied to the container's first child element (the Plot figure).
 * Double-click resets to 1:1.
 */
export function plotZoom(node: HTMLElement) {
    let scale = 1;
    let tx = 0;
    let ty = 0;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;
    let panTx = 0;
    let panTy = 0;

    node.style.cursor = 'grab';
    node.style.userSelect = 'none';

    function applyTransform() {
        const el = node.firstElementChild as HTMLElement | null;
        if (!el) return;
        el.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
        el.style.transformOrigin = '0 0';
    }

    function onWheel(e: WheelEvent) {
        e.preventDefault();
        const rect = node.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        const newScale = Math.max(0.25, Math.min(8, scale * factor));
        // Keep the point under the cursor fixed
        tx = mx - (mx - tx) * (newScale / scale);
        ty = my - (my - ty) * (newScale / scale);
        scale = newScale;
        applyTransform();
    }

    function onMouseDown(e: MouseEvent) {
        if (e.button !== 0) return;
        isPanning = true;
        panStartX = e.clientX;
        panStartY = e.clientY;
        panTx = tx;
        panTy = ty;
        node.style.cursor = 'grabbing';
    }

    function onMouseMove(e: MouseEvent) {
        if (!isPanning) return;
        tx = panTx + (e.clientX - panStartX);
        ty = panTy + (e.clientY - panStartY);
        applyTransform();
    }

    function onMouseUp() {
        if (!isPanning) return;
        isPanning = false;
        node.style.cursor = 'grab';
    }

    function onDblClick() {
        scale = 1;
        tx = 0;
        ty = 0;
        applyTransform();
    }

    node.addEventListener('wheel', onWheel, { passive: false });
    node.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    node.addEventListener('dblclick', onDblClick);

    return {
        destroy() {
            node.removeEventListener('wheel', onWheel);
            node.removeEventListener('mousedown', onMouseDown);
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
            node.removeEventListener('dblclick', onDblClick);
        }
    };
}
