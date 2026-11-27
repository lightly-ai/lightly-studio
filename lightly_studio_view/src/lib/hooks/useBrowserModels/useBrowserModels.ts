import { get, writable } from 'svelte/store';
import {
    createDetector,
    createTextPromptedDetector,
    fetchModelBytes,
    parseClassNames,
    readOnnxMetadata
} from '$lib/browserInference';

type Detector = Awaited<ReturnType<typeof createDetector>>;
type ExecutionProvider = Detector['executionProvider'];

interface BrowserModel {
    id: string;
    task: 'object_detection';
    // For a text-prompted model, the classes the user typed.
    class_names: string[];
    runsIn: 'browser';
    // Finds the objects that its class names describe, instead of a fixed set of classes.
    isTextPrompted: boolean;
    // The confidence that the Auto-label tools start with.
    defaultThreshold: number;
}

interface LoadProgress {
    modelId: string;
    loaded: number;
    total: number;
}

const DEFAULT_MODEL_ID = 'ltdetrv2-s-coco';
const DEFAULT_MODEL_URL = `/models/${DEFAULT_MODEL_ID}.onnx`;
const TEXT_PROMPTED_MODEL_ID = 'grounding-dino-tiny';
const DEFAULT_THRESHOLD = 0.5;
// Grounding DINO scores right objects around 0.3, so 0.5 misses most of them.
const TEXT_PROMPTED_THRESHOLD = 0.3;
const ONNX_EXTENSION = /\.onnx$/i;
// `?ep=wasm` forces the CPU runtime, to try the fallback on a machine with WebGPU.
const EXECUTION_PROVIDER_PARAM = 'ep';

const models = writable<BrowserModel[]>([
    toModel(DEFAULT_MODEL_ID, []),
    {
        ...toModel(TEXT_PROMPTED_MODEL_ID, []),
        isTextPrompted: true,
        defaultThreshold: TEXT_PROMPTED_THRESHOLD
    }
]);
const loadProgress = writable<LoadProgress | null>(null);
// A file the user loaded stays in memory until the tab closes.
const modelFiles = new Map<string, File>();
const detectors = new Map<string, Promise<Detector>>();

// The models that run in the browser: the default COCO model, Grounding DINO for classes the
// user types, and the ONNX files the user loaded.
export const useBrowserModels = () => ({
    models,
    loadProgress,
    getDetector,
    addModelFile,
    setPromptClassNames
});

// Sets the classes that a text-prompted model looks for.
const setPromptClassNames = (modelId: string, classNames: string[]) =>
    models.update((current) =>
        current.map((model) =>
            model.id === modelId ? { ...model, class_names: classNames } : model
        )
    );

// Loads each model once. Concurrent callers share the same detector.
const getDetector = (modelId: string): Promise<Detector> => {
    const existing = detectors.get(modelId);
    if (existing) return existing;
    const detector = loadDetector(modelId);
    detectors.set(modelId, detector);
    // A failed load is retried on the next call.
    detector.catch(() => detectors.delete(modelId));
    return detector;
};

// Registers an ONNX export of LightlyTrain and returns its model ID, from the file name.
const addModelFile = async (file: File): Promise<string> => {
    const metadata = readOnnxMetadata(new Uint8Array(await file.arrayBuffer()));
    const id = getUniqueId(file.name.replace(ONNX_EXTENSION, ''));
    modelFiles.set(id, file);
    models.update((current) => [
        ...current,
        toModel(id, parseClassNames(metadata.classes ?? '{}'))
    ]);
    return id;
};

const loadDetector = async (modelId: string): Promise<Detector> => {
    if (modelId === TEXT_PROMPTED_MODEL_ID) return loadTextPromptedDetector(modelId);
    const bytes = await readModelBytes(modelId);
    const detector = await createDetector(bytes, {
        executionProvider: getExecutionProviderOverride()
    });
    models.update((current) =>
        current.map((model) =>
            model.id === modelId ? { ...model, class_names: detector.classNames } : model
        )
    );
    return detector;
};

const loadTextPromptedDetector = async (modelId: string): Promise<Detector> => {
    try {
        return await createTextPromptedDetector({
            executionProvider: getExecutionProviderOverride(),
            onProgress: (loaded, total) => loadProgress.set({ modelId, loaded, total })
        });
    } finally {
        loadProgress.set(null);
    }
};

const readModelBytes = async (modelId: string): Promise<Uint8Array> => {
    const file = modelFiles.get(modelId);
    if (file) return new Uint8Array(await file.arrayBuffer());
    try {
        return await fetchModelBytes(DEFAULT_MODEL_URL, (loaded, total) =>
            loadProgress.set({ modelId, loaded, total })
        );
    } finally {
        loadProgress.set(null);
    }
};

const getUniqueId = (name: string): string => {
    const ids = new Set(get(models).map((model) => model.id));
    let id = name;
    for (let suffix = 2; ids.has(id); suffix++) id = `${name}-${suffix}`;
    return id;
};

const getExecutionProviderOverride = (): ExecutionProvider | undefined => {
    const value = new URLSearchParams(location.search).get(EXECUTION_PROVIDER_PARAM);
    return value === 'webgpu' || value === 'wasm' ? value : undefined;
};

function toModel(id: string, classNames: string[]): BrowserModel {
    return {
        id,
        task: 'object_detection',
        class_names: classNames,
        runsIn: 'browser',
        isTextPrompted: false,
        defaultThreshold: DEFAULT_THRESHOLD
    };
}
