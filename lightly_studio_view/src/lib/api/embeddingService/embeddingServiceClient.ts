/**
 * Client for a customer-hosted embedding service.
 *
 * The service runs on the customer's own network and serves the model their dataset was
 * indexed with. The browser calls it directly, so its vectors never pass through the
 * LightlyStudio backend and its weights never leave the customer's network.
 */

/** Timeout for the capability probe. Long enough for a cold service, short enough not to stall. */
const PROBE_TIMEOUT_MS = 3000;

/** Timeout for an embedding request, which may queue behind a model warm-up. */
const EMBED_TIMEOUT_MS = 30000;

interface ServiceInfo {
    contractVersion: string;
    modelId: string;
    embeddingDimension: number;
    supportsText: boolean;
    supportsImage: boolean;
    normalized: boolean;
}

/**
 * Fetch the service's model identity and capabilities.
 *
 * @throws If the service is unreachable, times out, or answers with a body that does not
 * match the contract.
 */
export async function fetchServiceInfo({
    servingUrl,
    timeoutMs = PROBE_TIMEOUT_MS
}: {
    servingUrl: string;
    timeoutMs?: number;
}): Promise<ServiceInfo> {
    const body = await requestJson({
        url: `${trimUrl(servingUrl)}/info`,
        init: { method: 'GET' },
        timeoutMs
    });
    return parseServiceInfo(body);
}

/** Embed a text query. Returns the raw vector the service produced. */
export async function embedTextViaService({
    servingUrl,
    text
}: {
    servingUrl: string;
    text: string;
}): Promise<number[]> {
    const body = await requestJson({
        url: `${trimUrl(servingUrl)}/embed/text`,
        init: {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        },
        timeoutMs: EMBED_TIMEOUT_MS
    });
    return parseEmbedding(body);
}

/** Embed a query image. The service owns all preprocessing. */
export async function embedImageViaService({
    servingUrl,
    file
}: {
    servingUrl: string;
    file: File;
}): Promise<number[]> {
    const form = new FormData();
    form.append('image', file, file.name);
    const body = await requestJson({
        url: `${trimUrl(servingUrl)}/embed/image`,
        init: { method: 'POST', body: form },
        timeoutMs: EMBED_TIMEOUT_MS
    });
    return parseEmbedding(body);
}

function trimUrl(servingUrl: string): string {
    return servingUrl.replace(/\/+$/, '');
}

async function requestJson({
    url,
    init,
    timeoutMs
}: {
    url: string;
    init: RequestInit;
    timeoutMs: number;
}): Promise<unknown> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { ...init, signal: controller.signal, mode: 'cors' });
        if (!response.ok) {
            throw new Error(`The embedding service at ${url} answered ${response.status}.`);
        }
        return await response.json();
    } catch (error) {
        // A blocked cross-origin or private-network request surfaces as an opaque
        // TypeError, so name the likely cause rather than repeating "Failed to fetch".
        if (error instanceof Error && error.name === 'AbortError') {
            throw new Error(
                `The embedding service at ${url} did not respond within ${timeoutMs}ms.`
            );
        }
        if (error instanceof TypeError) {
            throw new Error(
                `Could not reach the embedding service at ${url}. It may be down, or the browser ` +
                    `may have blocked the request because the service is not served over HTTPS or ` +
                    `does not allow this origin.`
            );
        }
        throw error;
    } finally {
        clearTimeout(timeout);
    }
}

function parseServiceInfo(body: unknown): ServiceInfo {
    if (typeof body !== 'object' || body === null) {
        throw new Error('The embedding service did not return a /info object.');
    }
    const info = body as Record<string, unknown>;
    const modelId = info.model_id;
    const embeddingDimension = info.embedding_dimension;
    if (typeof modelId !== 'string' || modelId === '') {
        throw new Error('The embedding service did not report a model_id.');
    }
    if (typeof embeddingDimension !== 'number' || !Number.isFinite(embeddingDimension)) {
        throw new Error(`The embedding service reported no embedding_dimension for '${modelId}'.`);
    }
    return {
        contractVersion: typeof info.contract_version === 'string' ? info.contract_version : '',
        modelId,
        embeddingDimension,
        // Absent capability flags default to unsupported: offering a search box that always
        // errors is worse than hiding one the model could have served.
        supportsText: info.supports_text === true,
        supportsImage: info.supports_image === true,
        normalized: info.normalized === true
    };
}

function parseEmbedding(body: unknown): number[] {
    if (
        !Array.isArray(body) ||
        body.length === 0 ||
        !body.every((value) => typeof value === 'number' && Number.isFinite(value))
    ) {
        throw new Error('The embedding service did not return a vector of numbers.');
    }
    return body as number[];
}
