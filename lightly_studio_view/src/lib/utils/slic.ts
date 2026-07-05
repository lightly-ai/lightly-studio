import {
    createMaskForLabels as createMaskForLabelsPkg,
    getLabelAtPoint as getLabelAtPointPkg,
    getSlicEngine,
    upsampleCellMask as upsampleCellMaskPkg,
    type Segmentation
} from '@lightly-ai/slic';
import { dev } from '$app/environment';
import { PUBLIC_SAMPLES_URL } from '$env/static/public';

export { extractCellMask } from '@lightly-ai/slic';

export type SlicLevel = 'coarse' | 'medium' | 'fine';

export type SlicResult = {
    labels: Int32Array;
    width: number;
    height: number;
    boundaries: Uint8Array;
    labelPixelIndexes: number[][];
    originalWidth: number;
    originalHeight: number;
    scaleX: number;
    scaleY: number;
    level: SlicLevel;
};

export type PreparedSlicImage = {
    imageData: ImageData;
    originalWidth: number;
    originalHeight: number;
    scaleX: number;
    scaleY: number;
};

const MAX_SLIC_EDGE = 512;

const LEVEL_CONFIG: Record<SlicLevel, { targetSegments: number; compactness: number }> = {
    coarse: { targetSegments: 80, compactness: 12 },
    medium: { targetSegments: 180, compactness: 10 },
    fine: { targetSegments: 320, compactness: 8 }
};

type BaseSlicData = {
    prepared: PreparedSlicImage;
    fine: Segmentation;
};

const baseResultCache = new Map<string, Promise<BaseSlicData>>();
const resultCache = new Map<string, Promise<SlicResult>>();

const stripTrailingSlash = (value: string) => value.replace(/\/+$/, '');

export const upsampleCellMask = (result: SlicResult, labelId: number) =>
    upsampleCellMaskPkg(result, labelId, result.originalWidth, result.originalHeight);

export const createSlicMaskForLabels = (result: SlicResult, labelIds: Iterable<number>) =>
    createMaskForLabelsPkg(result, labelIds);

export const getLabelAtPoint = (result: SlicResult, x: number, y: number) =>
    getLabelAtPointPkg(result, x, y, result.scaleX, result.scaleY);

export const maskToColoredDataUrl = (
    mask: Uint8Array,
    width: number,
    height: number,
    color: [number, number, number, number]
) => {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    if (!ctx) {
        throw new Error('Failed to create canvas for SLIC mask rendering');
    }

    const imageData = ctx.createImageData(width, height);

    for (let i = 0; i < mask.length; i++) {
        if (mask[i] !== 1) continue;

        const offset = i * 4;
        imageData.data[offset] = color[0];
        imageData.data[offset + 1] = color[1];
        imageData.data[offset + 2] = color[2];
        imageData.data[offset + 3] = color[3];
    }

    ctx.putImageData(imageData, 0, 0);
    return canvas.toDataURL();
};

export const resolveSlicImageUrl = (
    imageUrl: string,
    { isDev = dev, samplesUrl = PUBLIC_SAMPLES_URL }: { isDev?: boolean; samplesUrl?: string } = {}
) => {
    if (!isDev) {
        return imageUrl;
    }

    const normalizedSamplesUrl = stripTrailingSlash(samplesUrl);
    if (!normalizedSamplesUrl || !imageUrl.startsWith(`${normalizedSamplesUrl}/`)) {
        return imageUrl;
    }

    return imageUrl.replace(normalizedSamplesUrl, '/images');
};

export const prepareImageForSlic = async (
    imageUrl: string,
    maxEdge = MAX_SLIC_EDGE
): Promise<PreparedSlicImage> => {
    const resolvedImageUrl = resolveSlicImageUrl(imageUrl);

    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () =>
            reject(new Error(`Failed to decode image for SLIC: ${resolvedImageUrl}`));
        img.crossOrigin = 'anonymous';
        img.src = resolvedImageUrl;
    });

    const originalWidth = image.naturalWidth;
    const originalHeight = image.naturalHeight;

    const longestEdge = Math.max(originalWidth, originalHeight);
    const scale = longestEdge > maxEdge ? maxEdge / longestEdge : 1;
    const width = Math.max(1, Math.round(originalWidth * scale));
    const height = Math.max(1, Math.round(originalHeight * scale));

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    if (!ctx) {
        throw new Error('Failed to prepare image for SLIC');
    }

    ctx.drawImage(image, 0, 0, width, height);

    return {
        imageData: ctx.getImageData(0, 0, width, height),
        originalWidth,
        originalHeight,
        scaleX: originalWidth / width,
        scaleY: originalHeight / height
    };
};

const toSlicResult = (
    segmentation: Segmentation,
    prepared: PreparedSlicImage,
    level: SlicLevel
): SlicResult => ({
    labels: segmentation.labels,
    width: segmentation.width,
    height: segmentation.height,
    boundaries: segmentation.boundaries,
    labelPixelIndexes: segmentation.labelPixelIndexes,
    level,
    originalWidth: prepared.originalWidth,
    originalHeight: prepared.originalHeight,
    scaleX: prepared.scaleX,
    scaleY: prepared.scaleY
});

/**
 * Compute SLIC once at the finest level and derive coarser levels by merging
 * segments, so switching levels is cheap.
 */
const deriveHierarchicalResult = async (
    base: BaseSlicData,
    level: SlicLevel
): Promise<SlicResult> => {
    if (level === 'fine') {
        return toSlicResult(base.fine, base.prepared, level);
    }

    const engine = await getSlicEngine();
    const medium = engine.mergeSegments({
        labels: base.fine.labels,
        width: base.fine.width,
        height: base.fine.height,
        targetSegments: LEVEL_CONFIG.medium.targetSegments
    });

    if (level === 'medium') {
        return toSlicResult(medium, base.prepared, level);
    }

    const coarse = engine.mergeSegments({
        labels: medium.labels,
        width: medium.width,
        height: medium.height,
        targetSegments: LEVEL_CONFIG.coarse.targetSegments
    });

    return toSlicResult(coarse, base.prepared, level);
};

export const loadSuperpixelsForImage = async ({
    imageUrl,
    level
}: {
    imageUrl: string;
    level: SlicLevel;
}) => {
    const cacheKey = `${imageUrl}::${level}`;
    const cached = resultCache.get(cacheKey);
    if (cached) {
        return cached;
    }

    let basePending = baseResultCache.get(imageUrl);
    if (!basePending) {
        basePending = (async () => {
            const prepared = await prepareImageForSlic(imageUrl);
            const engine = await getSlicEngine();
            return {
                prepared,
                fine: engine.computeSuperpixels(prepared.imageData, {
                    targetSegments: LEVEL_CONFIG.fine.targetSegments,
                    compactness: LEVEL_CONFIG.fine.compactness
                })
            };
        })();
        baseResultCache.set(imageUrl, basePending);
    }

    const pending = basePending.then((base) => deriveHierarchicalResult(base, level));

    resultCache.set(cacheKey, pending);
    return pending;
};
