const MODEL_CACHE_NAME = 'lightly-browser-models';

// Downloads a model file once and keeps it in the browser's Cache Storage, so later visits
// skip the download. Reports the download progress in bytes.
export const fetchModelBytes = async (
    url: string,
    onProgress: (loaded: number, total: number) => void
): Promise<Uint8Array> => {
    // Cache Storage only exists in secure contexts, such as localhost or HTTPS.
    const cache = 'caches' in globalThis ? await caches.open(MODEL_CACHE_NAME) : null;
    const cached = await cache?.match(url);
    if (cached) return new Uint8Array(await cached.arrayBuffer());

    const response = await fetch(url);
    if (!response.ok || !response.body) {
        throw new Error(`Could not download the model from ${url}: HTTP ${response.status}.`);
    }
    const total = Number(response.headers.get('content-length') ?? 0);
    const bytes = await readWithProgress({ body: response.body, total, onProgress });
    await cache?.put(url, new Response(bytes));
    return bytes;
};

const readWithProgress = async ({
    body,
    total,
    onProgress
}: {
    body: ReadableStream<Uint8Array>;
    total: number;
    onProgress: (loaded: number, total: number) => void;
}): Promise<Uint8Array> => {
    const chunks: Uint8Array[] = [];
    let loaded = 0;
    for await (const chunk of body) {
        chunks.push(chunk);
        loaded += chunk.length;
        onProgress(loaded, total);
    }
    const bytes = new Uint8Array(loaded);
    let offset = 0;
    for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.length;
    }
    return bytes;
};
