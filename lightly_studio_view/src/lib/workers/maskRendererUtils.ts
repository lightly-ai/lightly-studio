import { rgbaFromBytes } from '$lib/utils/colorConvert';

export interface MaskInput {
    rle: ReadonlyArray<number>;
    color: [number, number, number, number];
}

export interface BoundingBoxInput {
    x: number;
    y: number;
    width: number;
    height: number;
    color: [number, number, number, number];
}

export interface SourceCrop {
    x: number;
    y: number;
    width: number;
    height: number;
}

/** Describes how source-image coordinates map onto the output canvas. */
export interface RenderGeometry {
    sourceWidth: number;
    sourceHeight: number;
    outputWidth: number;
    outputHeight: number;
    objectFit: 'contain' | 'cover';
    sourceCrop?: SourceCrop;
}

export interface RenderTransform {
    scale: number;
    offsetX: number;
    offsetY: number;
    viewport: SourceCrop;
}

export const getRenderTransform = ({
    sourceWidth,
    sourceHeight,
    outputWidth,
    outputHeight,
    objectFit,
    sourceCrop
}: RenderGeometry): RenderTransform => {
    const viewport = sourceCrop ?? { x: 0, y: 0, width: sourceWidth, height: sourceHeight };
    const scaleForWidth = outputWidth / viewport.width;
    const scaleForHeight = outputHeight / viewport.height;
    const scale =
        objectFit === 'cover'
            ? Math.max(scaleForWidth, scaleForHeight)
            : Math.min(scaleForWidth, scaleForHeight);

    return {
        scale,
        offsetX: (outputWidth - viewport.width * scale) / 2 - viewport.x * scale,
        offsetY: (outputHeight - viewport.height * scale) / 2 - viewport.y * scale,
        viewport
    };
};

const findRunIndex = (runEnds: number[], pixelIndex: number): number => {
    let low = 0;
    let high = runEnds.length;
    while (low < high) {
        const middle = Math.floor((low + high) / 2);
        if (pixelIndex < runEnds[middle]) high = middle;
        else low = middle + 1;
    }
    return low;
};

const getRunEnds = (rle: ReadonlyArray<number>): number[] => {
    const runEnds: number[] = [];
    let end = 0;
    for (const run of rle) {
        end += Math.max(0, Math.floor(Number(run) || 0));
        runEnds.push(end);
    }
    return runEnds;
};

/**
 * Renders source-sized RLE masks directly into an output-sized pixel buffer.
 * This keeps memory usage bounded by the visible canvas size.
 */
export const renderMasks = (
    geometry: RenderGeometry,
    masks: MaskInput[]
): Uint8ClampedArray<ArrayBuffer> => {
    const { sourceWidth, sourceHeight, outputWidth, outputHeight } = geometry;
    const pixelData = new Uint8ClampedArray(
        new ArrayBuffer(outputWidth * outputHeight * Uint8ClampedArray.BYTES_PER_ELEMENT * 4)
    );
    const { scale, offsetX, offsetY, viewport } = getRenderTransform(geometry);

    for (const { rle, color } of masks) {
        const runEnds = getRunEnds(rle);
        if (runEnds.length === 0) continue;

        for (let outputY = 0; outputY < outputHeight; outputY++) {
            const sourceY = Math.floor((outputY + 0.5 - offsetY) / scale);
            if (
                sourceY < 0 ||
                sourceY >= sourceHeight ||
                sourceY < viewport.y ||
                sourceY >= viewport.y + viewport.height
            )
                continue;

            for (let outputX = 0; outputX < outputWidth; outputX++) {
                const sourceX = Math.floor((outputX + 0.5 - offsetX) / scale);
                if (
                    sourceX < 0 ||
                    sourceX >= sourceWidth ||
                    sourceX < viewport.x ||
                    sourceX >= viewport.x + viewport.width
                )
                    continue;

                const runIndex = findRunIndex(runEnds, sourceY * sourceWidth + sourceX);
                if (runIndex >= runEnds.length || runIndex % 2 === 0) continue;

                const offset = (outputY * outputWidth + outputX) * 4;
                pixelData.set(color, offset);
            }
        }
    }
    return pixelData;
};

/** Clips bounding boxes to the visible source crop and maps them onto the output canvas. */
export const transformBoxes = (
    geometry: RenderGeometry,
    boxes: BoundingBoxInput[]
): BoundingBoxInput[] => {
    const { outputWidth, outputHeight } = geometry;
    const { sourceWidth, sourceHeight } = geometry;
    const { scale, offsetX, offsetY, viewport } = getRenderTransform(geometry);
    const viewportLeft = Math.max(0, viewport.x);
    const viewportTop = Math.max(0, viewport.y);
    const viewportRight = Math.min(sourceWidth, viewport.x + viewport.width);
    const viewportBottom = Math.min(sourceHeight, viewport.y + viewport.height);

    return boxes.flatMap((box) => {
        const sourceLeft = Math.max(viewportLeft, box.x);
        const sourceTop = Math.max(viewportTop, box.y);
        const sourceRight = Math.min(viewportRight, box.x + box.width);
        const sourceBottom = Math.min(viewportBottom, box.y + box.height);
        const left = Math.max(0, sourceLeft * scale + offsetX);
        const top = Math.max(0, sourceTop * scale + offsetY);
        const right = Math.min(outputWidth, sourceRight * scale + offsetX);
        const bottom = Math.min(outputHeight, sourceBottom * scale + offsetY);
        if (right <= left || bottom <= top) return [];
        return [{ ...box, x: left, y: top, width: right - left, height: bottom - top }];
    });
};

type BoxContext = Pick<
    CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
    'save' | 'restore' | 'lineWidth' | 'strokeStyle' | 'strokeRect'
>;

export const drawBoxesOnContext = (ctx: BoxContext, boxes: BoundingBoxInput[], stroke = 2) => {
    if (!boxes.length) return;
    ctx.save();
    ctx.lineWidth = stroke;
    for (const box of boxes) {
        ctx.strokeStyle = rgbaFromBytes(box.color);
        ctx.strokeRect(box.x, box.y, box.width, box.height);
    }
    ctx.restore();
};
