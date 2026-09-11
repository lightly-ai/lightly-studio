import { ProviderError } from './providerError';

/** A `sensor_msgs/msg/CompressedImage`. */
export interface CompressedImageMessage {
    readonly format: string;
    readonly data: Uint8Array;
}

/** A `sensor_msgs/msg/Image`: pixels, with the encoding needed to read them. */
export interface RawImageMessage {
    readonly height: number;
    readonly width: number;
    readonly encoding: string;
    readonly step: number;
    readonly data: Uint8Array;
}

const CONTAINERS = ['jpeg', 'png', 'webp', 'avif'] as const;
/** Bytes per pixel for the raw encodings this reads. */
const CHANNELS: Record<string, number> = { rgb8: 3, bgr8: 3, rgba8: 4, bgra8: 4, mono8: 1 };

/**
 * The image container a ROS `format` names.
 *
 * ROS writes anything from `jpeg` to `bgr8; jpeg compressed bgr8` in that field, so the
 * container is looked for inside it rather than the whole string being trusted.
 */
export function imageMediaType(format: string): string {
    const lowered = format.toLowerCase();
    const container = CONTAINERS.find((candidate) => lowered.includes(candidate));
    return `image/${container ?? (lowered.includes('jpg') ? 'jpeg' : 'jpeg')}`;
}

/** Decodes a compressed camera image, scaled to the width the caller will draw at. */
export async function decodeCompressedImage(
    message: CompressedImageMessage,
    maxWidth: number
): Promise<ImageBitmap> {
    const blob = new Blob([toArrayBuffer(message.data)], { type: imageMediaType(message.format) });
    return createImageBitmap(blob, resizeTo(maxWidth));
}

/** Converts a raw camera image to RGBA and decodes it at the width the caller will draw at. */
export async function decodeRawImage(
    message: RawImageMessage,
    maxWidth: number
): Promise<ImageBitmap> {
    const { width, height } = message;
    if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) || width < 1 || height < 1) {
        throw new ProviderError('corrupt', 'The camera image has no usable dimensions.');
    }
    return createImageBitmap(
        new ImageData(toRgba(message), width, height),
        resizeTo(maxWidth, width)
    );
}

function resizeTo(maxWidth: number, sourceWidth?: number) {
    if (sourceWidth !== undefined && sourceWidth <= maxWidth) return undefined;
    // Cheap resampling: these are thumbnails in a strip, not the pixels anyone inspects.
    return { resizeWidth: maxWidth, resizeQuality: 'low' as const };
}

/**
 * Rewrites a raw image's pixels as RGBA.
 *
 * Row start comes from `step` rather than from the width: a publisher is free to pad rows,
 * and reading them as tightly packed shears the picture.
 */
function toRgba(message: RawImageMessage) {
    const { width, height, step, data } = message;
    const encoding = message.encoding.toLowerCase();
    const channels = CHANNELS[encoding];
    if (channels === undefined) {
        throw new ProviderError('fields', `Camera images encoded as '${encoding}' are not read.`);
    }
    const rgba = new Uint8ClampedArray(width * height * 4);
    const [red, green, blue] = encoding.startsWith('bgr') ? [2, 1, 0] : [0, 1, 2];
    for (let row = 0; row < height; row++) {
        for (let column = 0; column < width; column++) {
            const from = row * step + column * channels;
            const to = (row * width + column) * 4;
            const grey = channels === 1;
            rgba[to] = data[from + (grey ? 0 : red)];
            rgba[to + 1] = data[from + (grey ? 0 : green)];
            rgba[to + 2] = data[from + (grey ? 0 : blue)];
            rgba[to + 3] = channels === 4 ? data[from + 3] : 255;
        }
    }
    return rgba;
}

function toArrayBuffer(data: Uint8Array): ArrayBuffer {
    return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) as ArrayBuffer;
}
