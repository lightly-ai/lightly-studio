export type MaskInput = {
    rle: number[];
    color: [number, number, number, number]; // RGBA 0-255
};

export type BoundingBoxInput = {
    x: number;
    y: number;
    width: number;
    height: number;
    color: [number, number, number, number]; // RGBA 0-255
};

export const decodeRLEToBinaryMask = (rle: number[], width: number, height: number): Uint8Array => {
    const mask = new Uint8Array(width * height);
    let idx = 0;
    let value = 0;

    for (const count of rle) {
        const end = idx + count;
        if (end > mask.length) {
            break;
        }
        mask.fill(value, idx, end);
        idx = end;
        value = value === 0 ? 1 : 0;
    }

    return mask;
};

export const renderMasks = (width: number, height: number, masks: MaskInput[]) => {
    const pixelData = new Uint8ClampedArray(width * height * 4);

    for (const { rle, color } of masks) {
        if (!rle?.length) {
            continue;
        }

        const mask = decodeRLEToBinaryMask(rle, width, height);

        for (let i = 0; i < mask.length; i++) {
            if (mask[i] !== 1) {
                continue;
            }

            const offset = i * 4;
            pixelData[offset] = color[0];
            pixelData[offset + 1] = color[1];
            pixelData[offset + 2] = color[2];
            pixelData[offset + 3] = color[3];
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
