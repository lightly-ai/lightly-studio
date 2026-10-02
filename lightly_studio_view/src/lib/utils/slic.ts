import { getSlicEngine } from '@lightly-ai/slic';
import { dev } from '$app/environment';
import { PUBLIC_SAMPLES_URL } from '$env/static/public';

type SlicLevel = 'coarse' | 'medium' | 'fine';

// Max width or height of the image we use for SLIC computation. Bigger images get resized.
const MAX_SLIC_EDGE = 512;

// Prototype presets trade boundary detail against the number of clicks needed to select a region.
const LEVEL_CONFIG: Record<
    SlicLevel,
    { targetSegments: number; compactness: number; smoothing: 'bilateral' }
> = {
    coarse: { targetSegments: 80, compactness: 35, smoothing: 'bilateral' },
    medium: { targetSegments: 240, compactness: 28, smoothing: 'bilateral' },
    fine: { targetSegments: 480, compactness: 22, smoothing: 'bilateral' }
};

const stripTrailingSlash = (value = '') => value.replace(/\/+$/, '');

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

export const prepareImageForSlic = async (imageUrl: string, maxEdge = MAX_SLIC_EDGE) => {
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

export const loadSuperpixelsForImage = async ({
    imageUrl,
    level
}: {
    imageUrl: string;
    level: SlicLevel;
}) => {
    const prepared = await prepareImageForSlic(imageUrl);
    const engine = await getSlicEngine();
    return {
        segmentation: engine.computeSuperpixels(prepared.imageData, getSlicComputeOptions(level)),
        scaleX: prepared.scaleX,
        scaleY: prepared.scaleY
    };
};
