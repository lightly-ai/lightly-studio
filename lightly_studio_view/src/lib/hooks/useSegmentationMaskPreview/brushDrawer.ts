import { getBrushAnchor, getStrokeSpans, type BrushSpan } from './brushFootprint';
import type { DrawBrushDotParams, DrawBrushLineParams, EnsureSourceMaskContext } from './types';

interface CreateBrushDrawerParams {
    ensureSourceMaskContext: EnsureSourceMaskContext;
}

export interface BrushDrawer {
    drawBrushDot: (params: DrawBrushDotParams) => void;
    drawBrushLine: (params: DrawBrushLineParams) => void;
}

// Brush strokes are filled as whole-pixel rects, so the mask gets no antialiased edges.
export function createBrushDrawer({
    ensureSourceMaskContext
}: CreateBrushDrawerParams): BrushDrawer {
    const drawBrushDot = ({
        point,
        brushSize,
        width,
        height,
        compositeOperation = 'source-over'
    }: DrawBrushDotParams) => {
        const context = ensureSourceMaskContext(width, height);
        if (!context) return;

        prepareContext(context, compositeOperation);
        const anchor = getBrushAnchor(point, brushSize);
        fillSpans(
            context,
            getStrokeSpans({ from: anchor, to: anchor, size: brushSize, width, height })
        );
    };

    const drawBrushLine = ({
        from,
        to,
        brushSize,
        width,
        height,
        compositeOperation = 'source-over'
    }: DrawBrushLineParams) => {
        const context = ensureSourceMaskContext(width, height);
        if (!context) return;

        prepareContext(context, compositeOperation);
        const strokeSpans = getStrokeSpans({
            from: getBrushAnchor(from, brushSize),
            to: getBrushAnchor(to, brushSize),
            size: brushSize,
            width,
            height
        });
        fillSpans(context, strokeSpans);
    };

    return {
        drawBrushDot,
        drawBrushLine
    };
}

function prepareContext(
    context: CanvasRenderingContext2D,
    compositeOperation: GlobalCompositeOperation
) {
    context.globalCompositeOperation = compositeOperation;
    context.fillStyle = 'black';
}

function fillSpans(context: CanvasRenderingContext2D, spans: BrushSpan[]) {
    for (const span of spans) {
        context.fillRect(span.xStart, span.y, span.width, 1);
    }
}
