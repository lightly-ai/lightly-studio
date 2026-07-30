import { getSlicEngine, type Segmentation } from '@lightly-ai/slic';
import { dev } from '$app/environment';
import { PUBLIC_SAMPLES_URL } from '$env/static/public';

export type SlicLevel = 'coarse' | 'medium' | 'fine';

export type SlicResult = {
    segmentation: Segmentation;
    sourceWidth: number;
    sourceHeight: number;
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
    segmentation,
    level,
    sourceWidth: prepared.originalWidth,
    sourceHeight: prepared.originalHeight,
    scaleX: prepared.scaleX,
    scaleY: prepared.scaleY
});

const computeLevelResult = async (prepared: PreparedSlicImage, level: SlicLevel) => {
    const engine = await getSlicEngine();
    const segmentation = engine.computeSuperpixels(prepared.imageData, {
        ...getSlicComputeOptions(level)
    });
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
