import { readEmbeddingModelOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { fetchServiceInfo } from '$lib/api/embeddingService/embeddingServiceClient';
import { createQuery } from '@tanstack/svelte-query';

/**
 * `builtin` — the model runs inside the LightlyStudio backend, which embeds queries.
 * `probing` — a customer-hosted service is configured and is being contacted.
 * `ready` — the service answered and serves the model this collection was indexed with.
 * `unreachable` — the service did not answer.
 * `model-mismatch` — the service serves a different model than the stored vectors.
 */
type Status = 'builtin' | 'probing' | 'ready' | 'unreachable' | 'model-mismatch';

interface Params {
    /** Returns the collection whose embedding model should be resolved. */
    getCollectionId: () => string;
}

/**
 * Resolve where search queries for a collection must be embedded.
 *
 * A collection indexed with a customer's own model has no live model in the hosted
 * backend, so queries are embedded by an HTTP service on the customer's network that the
 * browser calls directly. This hook finds that service and reports whether it can serve
 * the collection, so search is either correct or visibly unavailable — it never falls
 * back to the built-in model, whose vectors would produce a confidently ordered list of
 * garbage against custom-model embeddings.
 */
export function useEmbeddingService({ getCollectionId }: Params) {
    const modelQuery = createQuery(() => ({
        ...readEmbeddingModelOptions({ path: { collection_id: getCollectionId() } }),
        // A collection's model does not change while it is open.
        staleTime: Infinity
    }));

    const servingUrl = $derived(modelQuery.data?.serving_url ?? undefined);
    const expectedModelId = $derived(modelQuery.data?.embedding_model_hash);

    const probeQuery = createQuery(() => ({
        // Keyed on the model identity as well as the host, so two collections sharing a
        // model share one probe result.
        queryKey: ['embeddingService', servingUrl, expectedModelId],
        queryFn: () => fetchServiceInfo({ servingUrl: servingUrl as string }),
        enabled: servingUrl !== undefined,
        staleTime: Infinity,
        // The probe is the failure signal, so surface it rather than retrying behind a spinner.
        retry: false
    }));

    const status: Status = $derived.by(() => {
        if (servingUrl === undefined) return 'builtin';
        if (probeQuery.isError) return 'unreachable';
        if (!probeQuery.isSuccess) return 'probing';
        if (probeQuery.data.modelId !== expectedModelId) return 'model-mismatch';
        return 'ready';
    });

    const info = $derived(probeQuery.isSuccess ? probeQuery.data : undefined);

    return {
        /** Base URL to embed queries against, or undefined to use the LightlyStudio backend. */
        get servingUrl() {
            return servingUrl;
        },
        get status() {
            return status;
        },
        get canSearchText() {
            if (status === 'builtin') return true;
            return status === 'ready' && info?.supportsText === true;
        },
        get canSearchImage() {
            if (status === 'builtin') return true;
            return status === 'ready' && info?.supportsImage === true;
        },
        /** User-facing explanation when search is unavailable, else undefined. */
        get textDisabledReason() {
            return disabledReason({ status, servingUrl, expectedModelId, info, modality: 'text' });
        },
        get imageDisabledReason() {
            return disabledReason({ status, servingUrl, expectedModelId, info, modality: 'image' });
        },
        /** Contact the service again, so a restarted box recovers without a page reload. */
        reprobe() {
            if (servingUrl !== undefined) void probeQuery.refetch();
        }
    };
}

function disabledReason({
    status,
    servingUrl,
    expectedModelId,
    info,
    modality
}: {
    status: Status;
    servingUrl: string | undefined;
    expectedModelId: string | undefined;
    info: Awaited<ReturnType<typeof fetchServiceInfo>> | undefined;
    modality: 'text' | 'image';
}): string | undefined {
    if (status === 'builtin' || status === 'probing') return undefined;
    if (status === 'unreachable') {
        return `Search is unavailable: the embedding service at ${servingUrl} did not respond. Check that it is running and reachable from this machine.`;
    }
    if (status === 'model-mismatch') {
        return `Search is unavailable: the service at ${servingUrl} serves model '${info?.modelId}', but this collection was indexed with '${expectedModelId}'. Searching would compare vectors from two different embedding spaces.`;
    }
    if (modality === 'text' && info?.supportsText !== true) {
        return `This collection's embedding model cannot embed text. Search by image instead.`;
    }
    if (modality === 'image' && info?.supportsImage !== true) {
        return `This collection's embedding model cannot embed images. Search by text instead.`;
    }
    return undefined;
}
