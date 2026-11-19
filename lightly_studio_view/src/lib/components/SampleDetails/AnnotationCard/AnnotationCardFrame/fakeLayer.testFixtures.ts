const SVG_NS = 'http://www.w3.org/2000/svg';

type Matrix = { a: number; d: number; e: number; f: number };

/**
 * An annotation layer on an 800x600 canvas for tests, since jsdom has no layout. `setMatrix`
 * pans or zooms like ZoomableContainer: it changes the transform of an element above the layer.
 */
export const fakeLayer = (matrix: Matrix = { a: 1, d: 1, e: 0, f: 0 }) => {
    const canvas = document.createElementNS(SVG_NS, 'svg');
    const zoom = canvas.appendChild(document.createElementNS(SVG_NS, 'g'));
    const layer = zoom.appendChild(document.createElementNS(SVG_NS, 'g'));
    let current = matrix;
    canvas.getBoundingClientRect = () =>
        ({ left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600 }) as DOMRect;
    layer.getScreenCTM = () => current as DOMMatrix;
    document.body.appendChild(canvas);
    return {
        layer,
        setMatrix: (next: Matrix) => {
            current = next;
            zoom.setAttribute('transform', `translate(${next.e}, ${next.f}) scale(${next.a})`);
        }
    };
};
