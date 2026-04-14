import type { DrawBrushDotParams, DrawBrushLineParams, EnsureSourceMaskContext } from './types';

interface CreateBrushDrawerParams {
    ensureSourceMaskContext: EnsureSourceMaskContext;
}

export interface BrushDrawer {
    drawBrushDot: (params: DrawBrushDotParams) => void;
    drawBrushLine: (params: DrawBrushLineParams) => void;
}

export function createBrushDrawer({
    ensureSourceMaskContext
}: CreateBrushDrawerParams): BrushDrawer {
    const drawBrushDot = ({ point, brushRadius, width, height }: DrawBrushDotParams) => {
        const context = ensureSourceMaskContext(width, height);
        if (!context) return;

        context.globalCompositeOperation = 'source-over';
        context.fillStyle = 'black';
        context.beginPath();
        context.arc(point.x, point.y, brushRadius, 0, Math.PI * 2);
        context.fill();
    };

    const drawBrushLine = ({ from, to, brushRadius, width, height }: DrawBrushLineParams) => {
        const context = ensureSourceMaskContext(width, height);
        if (!context) return;

        context.globalCompositeOperation = 'source-over';
        context.strokeStyle = 'black';
        context.lineWidth = brushRadius * 2;
        context.lineCap = 'round';
        context.lineJoin = 'round';
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.stroke();
    };

    return {
        drawBrushDot,
        drawBrushLine
    };
}
