import { getBrushAnchor, getBrushSpans, getStrokeAnchors } from './brushFootprint';
import type {
    BrushPoint,
    DrawBrushDotParams,
    DrawBrushLineParams,
    EnsureSourceMaskContext
} from './types';

interface CreateBrushDrawerParams {
    ensureSourceMaskContext: EnsureSourceMaskContext;
}

export interface BrushDrawer {
    drawBrushDot: (params: DrawBrushDotParams) => void;
    drawBrushLine: (params: DrawBrushLineParams) => void;
}

// Brush strokes are stamped as whole-pixel rects, so the mask gets no antialiased edges.
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
        stampDisc(context, getBrushAnchor(point, brushSize), brushSize);
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
        const strokeAnchors = getStrokeAnchors(
            getBrushAnchor(from, brushSize),
            getBrushAnchor(to, brushSize)
        );
        for (const anchor of strokeAnchors) {
            stampDisc(context, anchor, brushSize);
        }
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

function stampDisc(context: CanvasRenderingContext2D, anchor: BrushPoint, brushSize: number) {
    for (const span of getBrushSpans(anchor, brushSize)) {
        context.fillRect(span.xStart, span.y, span.width, 1);
    }
}
