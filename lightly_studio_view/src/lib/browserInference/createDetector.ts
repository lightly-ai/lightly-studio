import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';
import { createPixelReader } from './createPixelReader';
import { decodeDetections, toInputTensor } from './detection';
import { loadOnnxSession, type ExecutionProvider } from './onnxSession';
import { parseClassNames, readOnnxMetadata } from './onnxMetadata';
import { runOneAtATime } from './runOneAtATime';

type InferenceSession = Awaited<ReturnType<typeof loadOnnxSession>>['session'];

interface Size {
    width: number;
    height: number;
}

export interface Detector {
    // The classes the model knows. Empty for a text-prompted model.
    classNames: string[];
    inputSize: Size;
    executionProvider: ExecutionProvider;
    // A text-prompted model finds promptClassNames, other models ignore it.
    detect: (
        image: ImageBitmap,
        original: Size,
        threshold: number,
        promptClassNames: string[]
    ) => Promise<ModelAnnotationPreview[]>;
}

// LightlyTrain keeps the 300 best (query, class) pairs, as many as the model has queries.
const TOP_K = 300;
const DEFAULT_INPUT_SIZE: Size = { width: 640, height: 640 };
const INPUT_NAME = 'images';
const RGB_CHANNELS = 3;

// Loads a LightlyTrain object detection ONNX export into onnxruntime-web.
export const createDetector = async (
    bytes: Uint8Array,
    options: { executionProvider?: ExecutionProvider } = {}
): Promise<Detector> => {
    const metadata = readOnnxMetadata(bytes);
    const classNames = parseClassNames(metadata.classes ?? '{}');
    const normalize = metadata.image_normalize ? JSON.parse(metadata.image_normalize) : null;
    const { ort, session, executionProvider } = await loadOnnxSession(
        bytes,
        options.executionProvider
    );
    const inputSize = readInputSize(session);
    const readPixels = createPixelReader(inputSize);

    const detect: Detector['detect'] = runOneAtATime(async (image, original, threshold) => {
        const input = toInputTensor({ rgba: readPixels(image), ...inputSize, normalize });
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

const readInputSize = (session: InferenceSession): Size => {
    const input = session.inputMetadata.find((metadata) => metadata.name === INPUT_NAME);
    const shape = input?.isTensor ? input.shape : [];
    const [, , height, width] = shape;
    const isFixedSize = typeof height === 'number' && typeof width === 'number';
    return isFixedSize ? { width, height } : DEFAULT_INPUT_SIZE;
};
