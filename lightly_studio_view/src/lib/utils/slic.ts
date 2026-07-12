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
    /** CSR pixel-index buffers; prefer these in hot paths. */
    pixelIndexes: Uint32Array;
    segmentOffsets: Uint32Array;
    /** Materialized lazily on first access — avoid in hot paths. */
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

const LEVEL_CONFIG: Record<
    SlicLevel,
    { targetSegments: number; compactness: number; smoothing: 'bilateral' }
> = {
    coarse: { targetSegments: 80, compactness: 35, smoothing: 'bilateral' },
    medium: { targetSegments: 240, compactness: 28, smoothing: 'bilateral' },
    fine: { targetSegments: 480, compactness: 22, smoothing: 'bilateral' }
};

const preparedImageCache = new Map<string, Promise<PreparedSlicImage>>();
const resultCache = new Map<string, Promise<SlicResult>>();

const stripTrailingSlash = (value: string) => value.replace(/\/+$/, '');

export const getSlicComputeOptions = (level: SlicLevel) => LEVEL_CONFIG[level];

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
    pixelIndexes: segmentation.pixelIndexes,
    segmentOffsets: segmentation.segmentOffsets,
    // Delegate instead of copying so the package's lazy materialization is
    // only triggered if something actually reads labelPixelIndexes.
    get labelPixelIndexes() {
        return segmentation.labelPixelIndexes;
    },
    level,
    originalWidth: prepared.originalWidth,
    originalHeight: prepared.originalHeight,
    scaleX: prepared.scaleX,
    scaleY: prepared.scaleY
});

const computeLevelResult = async (prepared: PreparedSlicImage, level: SlicLevel) => {
    const engine = await getSlicEngine();
    const start = performance.now();
    const segmentation = engine.computeSuperpixels(prepared.imageData, {
        ...getSlicComputeOptions(level)
    });
    const durationMs = performance.now() - start;
    console.log(
        `[slic] ${level}: ${segmentation.segmentCount} segments on ` +
            `${prepared.imageData.width}x${prepared.imageData.height} ` +
            `(${engine.backend} backend) in ${durationMs.toFixed(1)}ms`
    );
    return toSlicResult(segmentation, prepared, level);
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

    let preparedPending = preparedImageCache.get(imageUrl);
    if (!preparedPending) {
        preparedPending = prepareImageForSlic(imageUrl);
        preparedImageCache.set(imageUrl, preparedPending);
        void preparedPending.catch(() => {
            if (preparedImageCache.get(imageUrl) === preparedPending) {
                preparedImageCache.delete(imageUrl);
            }
        });
    }

    const pending = preparedPending.then((prepared) => computeLevelResult(prepared, level));

    resultCache.set(cacheKey, pending);
    void pending.catch(() => {
        if (resultCache.get(cacheKey) === pending) {
            resultCache.delete(cacheKey);
        }
    });
    return pending;
};
