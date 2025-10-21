/**
 * Interface for SVG elements that can maintain scale-independent transformations.
 * This is used to create elements that can maintain their visual size regardless
 * of parent SVG transformations.
 */
export interface ScaleIndependentElement extends SVGGraphicsElement {
    /** Optional transform that maintains scale independence */
    scaleIndependentXForm?: SVGTransform;
}

/**
 * Applies a transformation to an SVG element to make it appear scale-independent
 * relative to its parent SVG container. This is useful for creating elements that
 * maintain a consistent visual size regardless of parent SVG transformations.
 *
 * @param el - The SVG element to make scale-independent
 * @param svgContainer - The parent SVG container element
 * @throws {Error} If the element has no parent SVGGraphicsElement
 * @throws {Error} If the element has no screen CTM (Current Transform Matrix)
 */
export function unscale(el: ScaleIndependentElement, svgContainer: SVGSVGElement) {
    let xf = el.scaleIndependentXForm;
    if (!xf) {
        // Keep a single transform matrix in the stack for fighting transformations
        // Be sure to apply this transform after existing transforms (translate)
        xf = el.scaleIndependentXForm = svgContainer.createSVGTransform();
        el.transform.baseVal.appendItem(xf);
    }

    const parent = el.parentNode as SVGGraphicsElement | null;

    if (parent) {
        const matrix = parent.getScreenCTM();
        if (matrix) {
            const inversedMatrix = matrix.inverse().multiply(svgContainer.getScreenCTM()!);
            inversedMatrix.e = inversedMatrix.f = 0;
            xf.setMatrix(inversedMatrix);
        }
    }
}
