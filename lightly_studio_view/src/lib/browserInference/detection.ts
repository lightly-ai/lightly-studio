import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';

const RGBA_CHANNELS = 4;
const RGB_CHANNELS = 3;
const MAX_CHANNEL_VALUE = 255;
const BOX_VALUES = 4;

interface ImageNormalize {
    mean: number[];
    std: number[];
}

interface ToInputTensorParams {
    rgba: Uint8ClampedArray;
    width: number;
    height: number;
    normalize: ImageNormalize | null;
}

interface DecodeDetectionsParams {
    // Shape (queries, classes), raw logits.
    logits: Float32Array;
    // Shape (queries, 4), normalized center x, center y, width, height.
    boxes: Float32Array;
    numClasses: number;
    classNames: string[];
    imageWidth: number;
    imageHeight: number;
    threshold: number;
    topK: number;
}

// Turns canvas RGBA pixels into the CHW float input of a LightlyTrain detection model. The
// alpha channel is dropped, as LightlyTrain reads images as RGB.
export const toInputTensor = ({
    rgba,
    width,
    height,
    normalize
}: ToInputTensorParams): Float32Array => {
    const pixelCount = width * height;
    const tensor = new Float32Array(RGB_CHANNELS * pixelCount);
    for (let channel = 0; channel < RGB_CHANNELS; channel++) {
        const mean = normalize?.mean[channel] ?? 0;
        const std = normalize?.std[channel] ?? 1;
        for (let pixel = 0; pixel < pixelCount; pixel++) {
            const value = rgba[pixel * RGBA_CHANNELS + channel] / MAX_CHANNEL_VALUE;
            tensor[channel * pixelCount + pixel] = (value - mean) / std;
        }
    }
    return tensor;
};

// Decodes the raw model outputs like LightlyTrain's ObjectDetectionPostprocessor: the top k
// (query, class) scores above the threshold, as boxes in pixels of the original image.
export const decodeDetections = (params: DecodeDetectionsParams): ModelAnnotationPreview[] => {
    const scores = Array.from(params.logits, sigmoid);
    const topIndices = scores
        .map((_, index) => index)
        .sort((a, b) => scores[b] - scores[a])
        .slice(0, params.topK);
    return topIndices
        .filter((index) => scores[index] > params.threshold)
        .map((index) => toPreview({ index, score: scores[index], params }));
};

const toPreview = ({
    index,
    score,
    params
}: {
    index: number;
    score: number;
    params: DecodeDetectionsParams;
}): ModelAnnotationPreview => {
    const query = Math.floor(index / params.numClasses);
    const offset = query * BOX_VALUES;
    const [centerX, centerY, boxWidth, boxHeight] = params.boxes.subarray(
        offset,
        offset + BOX_VALUES
    );
    const left = Math.round((centerX - boxWidth / 2) * params.imageWidth);
    const top = Math.round((centerY - boxHeight / 2) * params.imageHeight);
    const right = Math.round((centerX + boxWidth / 2) * params.imageWidth);
    const bottom = Math.round((centerY + boxHeight / 2) * params.imageHeight);
    return {
        class_name: params.classNames[index % params.numClasses],
        bbox: { x: left, y: top, width: right - left, height: bottom - top },
        segmentation_mask: null,
        score
    };
};

const sigmoid = (logit: number) => 1 / (1 + Math.exp(-logit));
