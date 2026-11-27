type Ort = typeof import('onnxruntime-web/webgpu');
type InferenceSession = Awaited<ReturnType<Ort['InferenceSession']['create']>>;
export type ExecutionProvider = 'webgpu' | 'wasm';

const getWasmUrl = (version: string) =>
    `https://cdn.jsdelivr.net/npm/onnxruntime-web@${version}/dist/`;

// Creates an onnxruntime-web session. Prefers WebGPU and falls back to WASM where the
// browser has no WebGPU.
export const loadOnnxSession = async (
    bytes: Uint8Array,
    preferred: ExecutionProvider = getDefaultExecutionProvider()
): Promise<{ ort: Ort; session: InferenceSession; executionProvider: ExecutionProvider }> => {
    const ort = await import('onnxruntime-web/webgpu');
    ort.env.wasm.wasmPaths = getWasmUrl(ort.env.versions.web!);
    try {
        const session = await ort.InferenceSession.create(bytes, {
            executionProviders: [preferred]
        });
        return { ort, session, executionProvider: preferred };
    } catch (error) {
        if (preferred === 'wasm') throw error;
        console.warn('WebGPU is not usable, running the model on the CPU.', error);
        const session = await ort.InferenceSession.create(bytes, { executionProviders: ['wasm'] });
        return { ort, session, executionProvider: 'wasm' };
    }
};

const getDefaultExecutionProvider = (): ExecutionProvider =>
    'gpu' in navigator ? 'webgpu' : 'wasm';
