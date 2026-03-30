import { dev } from '$app/environment';
import { PUBLIC_SAMPLES_URL } from '$env/static/public';

export type SlicLevel = 'coarse' | 'medium' | 'fine';

export type SlicImageData = {
    data: Uint8ClampedArray;
    width: number;
    height: number;
};

export type SlicComputationOptions = {
    level: SlicLevel;
    compactness?: number;
    maxIterations?: number;
};

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
    fine: Omit<SlicResult, 'originalWidth' | 'originalHeight' | 'scaleX' | 'scaleY'>;
};

const baseResultCache = new Map<string, Promise<BaseSlicData>>();
const resultCache = new Map<string, Promise<SlicResult>>();

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);
const stripTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const rgbToLab = (r: number, g: number, b: number) => {
    const normalize = (value: number) => {
        const channel = value / 255;
        return channel <= 0.04045
            ? channel / 12.92
            : Math.pow((channel + 0.055) / 1.055, 2.4);
    };

    const rr = normalize(r);
    const gg = normalize(g);
    const bb = normalize(b);

    const x = (rr * 0.4124564 + gg * 0.3575761 + bb * 0.1804375) / 0.95047;
    const y = rr * 0.2126729 + gg * 0.7151522 + bb * 0.072175;
    const z = (rr * 0.0193339 + gg * 0.119192 + bb * 0.9503041) / 1.08883;

    const transform = (value: number) =>
        value > 0.008856 ? Math.cbrt(value) : 7.787 * value + 16 / 116;

    const fx = transform(x);
    const fy = transform(y);
    const fz = transform(z);

    return {
        l: 116 * fy - 16,
        a: 500 * (fx - fy),
        b: 200 * (fy - fz)
    };
};

const buildLabImage = (imageData: SlicImageData) => {
    const pixels = imageData.width * imageData.height;
    const lab = new Float32Array(pixels * 3);

    for (let i = 0; i < pixels; i++) {
        const offset = i * 4;
        const converted = rgbToLab(
            imageData.data[offset],
            imageData.data[offset + 1],
            imageData.data[offset + 2]
        );
        const labOffset = i * 3;
        lab[labOffset] = converted.l;
        lab[labOffset + 1] = converted.a;
        lab[labOffset + 2] = converted.b;
    }

    return lab;
};

const getMaxLabel = (labels: Int32Array) => {
    let maxLabel = -1;

    for (let i = 0; i < labels.length; i++) {
        if (labels[i] > maxLabel) {
            maxLabel = labels[i];
        }
    }

    return maxLabel;
};

const computeStep = (width: number, height: number, targetSegments: number) =>
    Math.max(4, Math.round(Math.sqrt((width * height) / Math.max(targetSegments, 1))));

export const computeBoundaryMask = (labels: Int32Array, width: number, height: number) => {
    const boundaries = new Uint8Array(width * height);

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const idx = y * width + x;
            const current = labels[idx];

            if (x > 0 && labels[idx - 1] !== current) {
                boundaries[idx] = 1;
                continue;
            }

            if (x < width - 1 && labels[idx + 1] !== current) {
                boundaries[idx] = 1;
                continue;
            }

            if (y > 0 && labels[idx - width] !== current) {
                boundaries[idx] = 1;
                continue;
            }

            if (y < height - 1 && labels[idx + width] !== current) {
                boundaries[idx] = 1;
            }
        }
    }

    return boundaries;
};

export const buildLabelPixelIndexes = (labels: Int32Array) => {
    const maxLabel = getMaxLabel(labels);
    const counts = new Uint32Array(maxLabel + 1);

    for (let i = 0; i < labels.length; i++) {
        counts[labels[i]] += 1;
    }

    const labelPixelIndexes = Array.from({ length: maxLabel + 1 }, (_, labelId) => {
        return new Array<number>(counts[labelId]);
    });
    const offsets = new Uint32Array(maxLabel + 1);

    for (let i = 0; i < labels.length; i++) {
        const labelId = labels[i];
        labelPixelIndexes[labelId][offsets[labelId]] = i;
        offsets[labelId] += 1;
    }

    return labelPixelIndexes;
};

export const computeSuperpixels = (
    imageData: SlicImageData,
    options: SlicComputationOptions
): Omit<SlicResult, 'originalWidth' | 'originalHeight' | 'scaleX' | 'scaleY'> => {
    const { width, height } = imageData;
    const config = LEVEL_CONFIG[options.level];
    const compactness = options.compactness ?? config.compactness;
    const maxIterations = options.maxIterations ?? 4;
    const step = computeStep(width, height, config.targetSegments);
    const lab = buildLabImage(imageData);

    const centersX: number[] = [];
    const centersY: number[] = [];
    const centersL: number[] = [];
    const centersA: number[] = [];
    const centersB: number[] = [];

    for (let y = Math.floor(step / 2); y < height; y += step) {
        for (let x = Math.floor(step / 2); x < width; x += step) {
            const idx = y * width + x;
            const labOffset = idx * 3;
            centersX.push(x);
            centersY.push(y);
            centersL.push(lab[labOffset]);
            centersA.push(lab[labOffset + 1]);
            centersB.push(lab[labOffset + 2]);
        }
    }

    const labels = new Int32Array(width * height);
    labels.fill(-1);

    const distances = new Float32Array(width * height);
    const spatialWeight = compactness / step;

    for (let iteration = 0; iteration < maxIterations; iteration++) {
        distances.fill(Number.POSITIVE_INFINITY);

        for (let cluster = 0; cluster < centersX.length; cluster++) {
            const centerX = centersX[cluster];
            const centerY = centersY[cluster];
            const minX = clamp(Math.floor(centerX - step), 0, width - 1);
            const maxX = clamp(Math.ceil(centerX + step), 0, width - 1);
            const minY = clamp(Math.floor(centerY - step), 0, height - 1);
            const maxY = clamp(Math.ceil(centerY + step), 0, height - 1);

            for (let y = minY; y <= maxY; y++) {
                for (let x = minX; x <= maxX; x++) {
                    const idx = y * width + x;
                    const labOffset = idx * 3;
                    const dl = lab[labOffset] - centersL[cluster];
                    const da = lab[labOffset + 1] - centersA[cluster];
                    const db = lab[labOffset + 2] - centersB[cluster];
                    const dx = x - centerX;
                    const dy = y - centerY;
                    const colorDistance = dl * dl + da * da + db * db;
                    const spatialDistance = dx * dx + dy * dy;
                    const distance = colorDistance + spatialDistance * spatialWeight * spatialWeight;

                    if (distance < distances[idx]) {
                        distances[idx] = distance;
                        labels[idx] = cluster;
                    }
                }
            }
        }

        const sumsX = new Float32Array(centersX.length);
        const sumsY = new Float32Array(centersX.length);
        const sumsL = new Float32Array(centersX.length);
        const sumsA = new Float32Array(centersX.length);
        const sumsB = new Float32Array(centersX.length);
        const counts = new Uint32Array(centersX.length);

        for (let idx = 0; idx < labels.length; idx++) {
            const cluster = labels[idx];
            if (cluster < 0) continue;

            const x = idx % width;
            const y = Math.floor(idx / width);
            const labOffset = idx * 3;
            sumsX[cluster] += x;
            sumsY[cluster] += y;
            sumsL[cluster] += lab[labOffset];
            sumsA[cluster] += lab[labOffset + 1];
            sumsB[cluster] += lab[labOffset + 2];
            counts[cluster] += 1;
        }

        for (let cluster = 0; cluster < centersX.length; cluster++) {
            if (counts[cluster] === 0) continue;

            centersX[cluster] = sumsX[cluster] / counts[cluster];
            centersY[cluster] = sumsY[cluster] / counts[cluster];
            centersL[cluster] = sumsL[cluster] / counts[cluster];
            centersA[cluster] = sumsA[cluster] / counts[cluster];
            centersB[cluster] = sumsB[cluster] / counts[cluster];
        }
    }

    return {
        labels,
        width,
        height,
        boundaries: computeBoundaryMask(labels, width, height),
        labelPixelIndexes: buildLabelPixelIndexes(labels),
        level: options.level
    };
};

const computeLabelCentroids = (labels: Int32Array, width: number, height: number) => {
    const maxLabel = getMaxLabel(labels);
    const sumsX = new Float32Array(maxLabel + 1);
    const sumsY = new Float32Array(maxLabel + 1);
    const counts = new Uint32Array(maxLabel + 1);

    for (let idx = 0; idx < labels.length; idx++) {
        const label = labels[idx];
        if (label < 0) continue;

        sumsX[label] += idx % width;
        sumsY[label] += Math.floor(idx / width);
        counts[label] += 1;
    }

    return { sumsX, sumsY, counts };
};

const relabelSequentially = (labels: Int32Array) => {
    const mapping = new Map<number, number>();
    const nextLabels = new Int32Array(labels.length);
    let nextId = 0;

    for (let i = 0; i < labels.length; i++) {
        const current = labels[i];
        let mapped = mapping.get(current);

        if (mapped === undefined) {
            mapped = nextId++;
            mapping.set(current, mapped);
        }

        nextLabels[i] = mapped;
    }

    return nextLabels;
};

export const deriveMergedLevel = ({
    sourceLabels,
    width,
    height,
    targetSegments
}: {
    sourceLabels: Int32Array;
    width: number;
    height: number;
    targetSegments: number;
}) => {
    const { sumsX, sumsY, counts } = computeLabelCentroids(sourceLabels, width, height);
    const coarseStep = computeStep(width, height, targetSegments);
    const gridWidth = Math.max(1, Math.ceil(width / coarseStep));
    const gridHeight = Math.max(1, Math.ceil(height / coarseStep));
    const parentByLabel = new Int32Array(counts.length);
    parentByLabel.fill(-1);

    for (let label = 0; label < counts.length; label++) {
        if (counts[label] === 0) continue;

        const centroidX = sumsX[label] / counts[label];
        const centroidY = sumsY[label] / counts[label];
        const bucketX = clamp(Math.floor(centroidX / coarseStep), 0, gridWidth - 1);
        const bucketY = clamp(Math.floor(centroidY / coarseStep), 0, gridHeight - 1);
        parentByLabel[label] = bucketY * gridWidth + bucketX;
    }

    const mergedLabels = new Int32Array(sourceLabels.length);
    for (let i = 0; i < sourceLabels.length; i++) {
        mergedLabels[i] = parentByLabel[sourceLabels[i]];
    }

    return relabelSequentially(mergedLabels);
};

const deriveHierarchicalResult = (base: BaseSlicData, level: SlicLevel): SlicResult => {
    let labels = base.fine.labels;

    if (level === 'medium') {
        labels = deriveMergedLevel({
            sourceLabels: base.fine.labels,
            width: base.fine.width,
            height: base.fine.height,
            targetSegments: LEVEL_CONFIG.medium.targetSegments
        });
    } else if (level === 'coarse') {
        const mediumLabels = deriveMergedLevel({
            sourceLabels: base.fine.labels,
            width: base.fine.width,
            height: base.fine.height,
            targetSegments: LEVEL_CONFIG.medium.targetSegments
        });
        labels = deriveMergedLevel({
            sourceLabels: mediumLabels,
            width: base.fine.width,
            height: base.fine.height,
            targetSegments: LEVEL_CONFIG.coarse.targetSegments
        });
    }

    return {
        labels,
        width: base.fine.width,
        height: base.fine.height,
        boundaries: computeBoundaryMask(labels, base.fine.width, base.fine.height),
        labelPixelIndexes: buildLabelPixelIndexes(labels),
        level,
        originalWidth: base.prepared.originalWidth,
        originalHeight: base.prepared.originalHeight,
        scaleX: base.prepared.scaleX,
        scaleY: base.prepared.scaleY
    };
};

export const extractCellMask = (
    labels: Int32Array,
    width: number,
    height: number,
    labelId: number
) => {
    const mask = new Uint8Array(width * height);

    for (let i = 0; i < labels.length; i++) {
        if (labels[i] === labelId) {
            mask[i] = 1;
        }
    }

    return mask;
};

export const upsampleCellMask = (result: SlicResult, labelId: number) => {
    const mask = new Uint8Array(result.originalWidth * result.originalHeight);

    for (let y = 0; y < result.originalHeight; y++) {
        const slicY = clamp(Math.floor(y / result.scaleY), 0, result.height - 1);

        for (let x = 0; x < result.originalWidth; x++) {
            const slicX = clamp(Math.floor(x / result.scaleX), 0, result.width - 1);
            const slicIndex = slicY * result.width + slicX;

            if (result.labels[slicIndex] === labelId) {
                mask[y * result.originalWidth + x] = 1;
            }
        }
    }

    return mask;
};

export const forEachOriginalPixelRangeForLabel = (
    result: SlicResult,
    labelId: number,
    callback: (startX: number, endX: number, startY: number, endY: number) => void
) => {
    const pixelIndexes = result.labelPixelIndexes[labelId] ?? [];

    for (const pixelIndex of pixelIndexes) {
        const slicX = pixelIndex % result.width;
        const slicY = Math.floor(pixelIndex / result.width);
        const startX = Math.min(
            result.originalWidth - 1,
            Math.max(0, Math.floor(slicX * result.scaleX))
        );
        const endX = Math.min(
            result.originalWidth,
            Math.max(startX + 1, Math.ceil((slicX + 1) * result.scaleX))
        );
        const startY = Math.min(
            result.originalHeight - 1,
            Math.max(0, Math.floor(slicY * result.scaleY))
        );
        const endY = Math.min(
            result.originalHeight,
            Math.max(startY + 1, Math.ceil((slicY + 1) * result.scaleY))
        );

        callback(startX, endX, startY, endY);
    }
};

export const createSlicMaskForLabels = (
    result: SlicResult,
    labelIds: Iterable<number>
) => {
    const mask = new Uint8Array(result.width * result.height);

    for (const labelId of labelIds) {
        const pixelIndexes = result.labelPixelIndexes[labelId];
        if (!pixelIndexes) continue;

        for (const pixelIndex of pixelIndexes) {
            mask[pixelIndex] = 1;
        }
    }

    return mask;
};

export const getLabelAtPoint = (result: SlicResult, x: number, y: number) => {
    const mappedX = clamp(Math.floor(x / result.scaleX), 0, result.width - 1);
    const mappedY = clamp(Math.floor(y / result.scaleY), 0, result.height - 1);
    return result.labels[mappedY * result.width + mappedX];
};

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
    {
        isDev = dev,
        samplesUrl = PUBLIC_SAMPLES_URL
    }: { isDev?: boolean; samplesUrl?: string } = {}
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
        img.onerror = () => reject(new Error(`Failed to decode image for SLIC: ${resolvedImageUrl}`));
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
    const cacheKey = `${imageUrl}::${level}`;
    const cached = resultCache.get(cacheKey);
    if (cached) {
        return cached;
    }

    let basePending = baseResultCache.get(imageUrl);
    if (!basePending) {
        basePending = prepareImageForSlic(imageUrl).then((prepared) => ({
            prepared,
            fine: computeSuperpixels(prepared.imageData, { level: 'fine' })
        }));
        baseResultCache.set(imageUrl, basePending);
    }

    const pending = basePending.then((base) => deriveHierarchicalResult(base, level));

    resultCache.set(cacheKey, pending);
    return pending;
};
