import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';
import { decodeDetections, toInputTensor } from './detection';
import { parseClassNames, readOnnxMetadata } from './onnxMetadata';
import { runOneAtATime } from './runOneAtATime';

type Ort = typeof import('onnxruntime-web/webgpu');
type InferenceSession = Awaited<ReturnType<Ort['InferenceSession']['create']>>;
type ExecutionProvider = 'webgpu' | 'wasm';

interface Size {
    width: number;
    height: number;
}

interface Detector {
    classNames: string[];
    inputSize: Size;
    executionProvider: ExecutionProvider;
    detect: (
        image: ImageBitmap,
        original: Size,
        threshold: number
    ) => Promise<ModelAnnotationPreview[]>;
}

// LightlyTrain keeps the 300 best (query, class) pairs, as many as the model has queries.
const TOP_K = 300;
const DEFAULT_INPUT_SIZE: Size = { width: 640, height: 640 };
const INPUT_NAME = 'images';
const RGB_CHANNELS = 3;
const getWasmUrl = (version: string) =>
    `https://cdn.jsdelivr.net/npm/onnxruntime-web@${version}/dist/`;

// Loads a LightlyTrain object detection ONNX export into onnxruntime-web. Prefers WebGPU and
// falls back to WASM where the browser has no WebGPU.
export const createDetector = async (
    bytes: Uint8Array,
    options: { executionProvider?: ExecutionProvider } = {}
): Promise<Detector> => {
    const ort = await import('onnxruntime-web/webgpu');
    ort.env.wasm.wasmPaths = getWasmUrl(ort.env.versions.web!);
    const metadata = readOnnxMetadata(bytes);
    const classNames = parseClassNames(metadata.classes ?? '{}');
    const normalize = metadata.image_normalize ? JSON.parse(metadata.image_normalize) : null;
    const { session, executionProvider } = await createSession({
        ort,
        bytes,
        preferred: options.executionProvider ?? getDefaultExecutionProvider()
    });
    const inputSize = readInputSize(session);
    const context = new OffscreenCanvas(inputSize.width, inputSize.height).getContext('2d', {
        willReadFrequently: true
    })!;
    // Replaces the pixels on each draw, so transparent areas never show the previous image.
    context.globalCompositeOperation = 'copy';

    const detect: Detector['detect'] = runOneAtATime(async (image, original, threshold) => {
        context.drawImage(image, 0, 0, inputSize.width, inputSize.height);
        const { data: rgba } = context.getImageData(0, 0, inputSize.width, inputSize.height);
        const input = toInputTensor({ rgba, ...inputSize, normalize });
        const dims = [1, RGB_CHANNELS, inputSize.height, inputSize.width];
        const outputs = await session.run({
            [INPUT_NAME]: new ort.Tensor('float32', input, dims)
        });
        const logits = outputs.logits.data as Float32Array;
        return decodeDetections({
            logits,
            boxes: outputs.boxes.data as Float32Array,
            numClasses: outputs.logits.dims.at(-1)!,
            classNames,
            imageWidth: original.width,
            imageHeight: original.height,
            threshold,
            topK: TOP_K
        });
    });

    return { classNames, inputSize, executionProvider, detect };
};

const getDefaultExecutionProvider = (): ExecutionProvider =>
    'gpu' in navigator ? 'webgpu' : 'wasm';

const createSession = async ({
    ort,
    bytes,
    preferred
}: {
    ort: Ort;
    bytes: Uint8Array;
    preferred: ExecutionProvider;
}): Promise<{ session: InferenceSession; executionProvider: ExecutionProvider }> => {
    try {
        const session = await ort.InferenceSession.create(bytes, {
            executionProviders: [preferred]
        });
        return { session, executionProvider: preferred };
    } catch (error) {
        if (preferred === 'wasm') throw error;
        console.warn('WebGPU is not usable, running the model on the CPU.', error);
        const session = await ort.InferenceSession.create(bytes, { executionProviders: ['wasm'] });
        return { session, executionProvider: 'wasm' };
    }
};

const readInputSize = (session: InferenceSession): Size => {
    const input = session.inputMetadata.find((metadata) => metadata.name === INPUT_NAME);
    const shape = input?.isTensor ? input.shape : [];
    const [, , height, width] = shape;
    const isFixedSize = typeof height === 'number' && typeof width === 'number';
    return isFixedSize ? { width, height } : DEFAULT_INPUT_SIZE;
};
