export type MaskInput = {
    rle: ReadonlyArray<number>;
    color: [number, number, number, number]; // RGBA 0-255
};

export type BoundingBoxInput = {
    x: number;
    y: number;
    width: number;
    height: number;
    color: [number, number, number, number]; // RGBA 0-255
};

export const renderMasks = (width: number, height: number, masks: MaskInput[]) => {
    const pixelData = new Uint8ClampedArray(width * height * 4);
    const maxPixels = width * height;

    for (const { rle, color } of masks) {
        if (!rle?.length) {
            continue;
        }

        // Decode RLE runs directly into RGBA output to avoid allocating an intermediate mask.
        let pixelIndex = 0;
        let value = 0;

        for (let runIndex = 0; runIndex < rle.length && pixelIndex < maxPixels; runIndex++) {
            const count = Math.max(0, Math.floor(Number(rle[runIndex]) || 0));
            const end = Math.min(pixelIndex + count, maxPixels);

            if (value === 1) {
                for (let i = pixelIndex; i < end; i++) {
                    const offset = i * 4;
                    pixelData[offset] = color[0];
                    pixelData[offset + 1] = color[1];
                    pixelData[offset + 2] = color[2];
                    pixelData[offset + 3] = color[3];
                }
            }

            pixelIndex = end;
            value = value === 0 ? 1 : 0;
        }
    }

    return pixelData;
};

export const computeStroke = (scaleX = 1, scaleY = 1) => {
    const scale = Math.max(scaleX, scaleY) || 1;
    return 2 / scale;
};

export const drawBoxesOnContext = (
    ctx: OffscreenCanvasRenderingContext2D,
    boxes: BoundingBoxInput[],
    width: number,
    height: number,
    stroke: number
) => {
    if (!boxes.length) return;

    ctx.save();
    ctx.lineWidth = stroke;
    const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

    for (const box of boxes) {
        const color = `rgba(${box.color[0]}, ${box.color[1]}, ${box.color[2]}, ${box.color[3] / 255})`;
        ctx.strokeStyle = color;

        const x = clamp(box.x, 0, width);
        const y = clamp(box.y, 0, height);
        const w = clamp(box.width, 0, width - x);
        const h = clamp(box.height, 0, height - y);

        if (w === 0 || h === 0) {
            continue;
        }

        ctx.strokeRect(x, y, w, h);
    }

    ctx.restore();
};
