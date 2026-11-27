import type { Detector } from './createDetector';
import { createPixelReader } from './createPixelReader';
import { toInputTensor } from './detection';
import { fetchModelBytes } from './fetchModelBytes';
import { decodeGroundedDetections, toPhraseSpans } from './groundedDetection';
import { loadOnnxSession, type ExecutionProvider } from './onnxSession';
import { runOneAtATime } from './runOneAtATime';

interface Tokenizer {
    encode: (text: string, options?: { add_special_tokens: boolean }) => number[];
    all_special_ids: number[];
}

// The subset of transformers.js that this detector uses.
interface Transformers {
    AutoTokenizer: { from_pretrained: (id: string) => Promise<Tokenizer> };
}

const MODEL_ID = 'onnx-community/grounding-dino-tiny-ONNX';
// fp16 is 360 MB. The 4-bit and fp16 files give NaN in the onnxruntime-web that transformers.js
// bundles, so the model runs on our own onnxruntime-web and transformers.js only tokenizes.
const MODEL_URL = `https://huggingface.co/${MODEL_ID}/resolve/main/onnx/model_fp16.onnx`;
const TRANSFORMERS_URL = 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/+esm';
// The export has a fixed 800×800 input. The processor stretches the image without padding.
const INPUT_SIZE = { width: 800, height: 800 };
const IMAGENET_NORMALIZE = { mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225] };
const RGB_CHANNELS = 3;

// Loads Grounding DINO tiny, which finds the objects that a list of class names describes.
export const createTextPromptedDetector = async ({
    executionProvider,
    onProgress
}: {
    executionProvider?: ExecutionProvider;
    onProgress: (loaded: number, total: number) => void;
}): Promise<Detector> => {
    const transformers = (await import(/* @vite-ignore */ TRANSFORMERS_URL)) as Transformers;
    const tokenizer = await transformers.AutoTokenizer.from_pretrained(MODEL_ID);
    const bytes = await fetchModelBytes(MODEL_URL, onProgress);
    const loaded = await loadOnnxSession(bytes, executionProvider);
    const { ort, session } = loaded;
    const tokens = {
        specialIds: new Set(tokenizer.all_special_ids),
        separatorId: tokenizer.encode('.', { add_special_tokens: false })[0]
    };
    const readPixels = createPixelReader(INPUT_SIZE);
    const { width, height } = INPUT_SIZE;
    const toInt64 = (values: number[], dims: number[]) =>
        new ort.Tensor('int64', BigInt64Array.from(values, BigInt), dims);
    // No padding, so every pixel is valid.
    const pixelMask = new ort.Tensor('int64', new BigInt64Array(width * height).fill(1n), [
        1,
        height,
        width
    ]);

    const detect: Detector['detect'] = runOneAtATime(
        async (image, original, threshold, promptClassNames) => {
            const inputIds = tokenizer.encode(toPrompt(promptClassNames));
            const textDims = [1, inputIds.length];
            const pixels = toInputTensor({
                rgba: readPixels(image),
                width,
                height,
                normalize: IMAGENET_NORMALIZE
            });
            const outputs = await session.run({
                pixel_values: new ort.Tensor('float32', pixels, [1, RGB_CHANNELS, height, width]),
                input_ids: toInt64(inputIds, textDims),
                token_type_ids: toInt64(new Array(inputIds.length).fill(0), textDims),
                attention_mask: toInt64(new Array(inputIds.length).fill(1), textDims),
                pixel_mask: pixelMask
            });
            return decodeGroundedDetections({
                logits: outputs.logits.data as Float32Array,
                boxes: outputs.pred_boxes.data as Float32Array,
                numTokens: outputs.logits.dims.at(-1)!,
                spans: toPhraseSpans(inputIds, tokens),
                classNames: promptClassNames,
                imageWidth: original.width,
                imageHeight: original.height,
                threshold
            });
        }
    );

    return {
        classNames: [],
        inputSize: INPUT_SIZE,
        executionProvider: loaded.executionProvider,
        detect
    };
};

// Grounding DINO expects lowercase phrases that each end with a dot: "forklift. pallet.".
const toPrompt = (classNames: string[]) =>
    classNames.map((name) => `${name.toLowerCase()}.`).join(' ');
