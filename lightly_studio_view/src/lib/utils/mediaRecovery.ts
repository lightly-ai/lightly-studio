import { getFeatures } from '$lib/api/lightly_studio_local/sdk.gen';

export const MEDIA_RECOVERY_WATCHDOG_MS = 10_000;

let mediaDirectUrlsEnabledPromise: Promise<boolean> | undefined;

export function withProxyMediaMode(url: string): string {
    if (url.startsWith('blob:') || url.startsWith('data:')) {
        return url;
    }

    const hashIndex = url.indexOf('#');
    const hash = hashIndex === -1 ? '' : url.slice(hashIndex);
    const urlWithoutHash = hashIndex === -1 ? url : url.slice(0, hashIndex);
    const queryIndex = urlWithoutHash.indexOf('?');
    const baseUrl = queryIndex === -1 ? urlWithoutHash : urlWithoutHash.slice(0, queryIndex);
    const params = new URLSearchParams(
        queryIndex === -1 ? undefined : urlWithoutHash.slice(queryIndex + 1)
    );
    params.set('mode', 'proxy');
    return `${baseUrl}?${params.toString()}${hash}`;
}

export async function isMediaDirectUrlsEnabled(): Promise<boolean> {
    mediaDirectUrlsEnabledPromise ??= getFeatures()
        .then((response) => response.data?.includes('media-direct-urls') ?? false)
        .catch(() => false);
    return mediaDirectUrlsEnabledPromise;
}

export async function resolveImageMediaSource(
    sourceUrl: string,
    signal: AbortSignal
): Promise<string | null> {
    if (!(await isMediaDirectUrlsEnabled())) {
        return sourceUrl;
    }
    if (await probeImageSource(sourceUrl, signal)) {
        return sourceUrl;
    }

    const proxyUrl = withProxyMediaMode(sourceUrl);
    return (await probeImageSource(proxyUrl, signal)) ? proxyUrl : null;
}

function probeImageSource(sourceUrl: string, signal: AbortSignal): Promise<boolean> {
    if (signal.aborted) return Promise.resolve(false);

    return new Promise((resolve) => {
        const image = new Image();
        const finish = (loaded: boolean) => {
            image.onload = null;
            image.onerror = null;
            signal.removeEventListener('abort', handleAbort);
            resolve(loaded && !signal.aborted);
        };
        const handleAbort = () => finish(false);
        image.onload = () => finish(true);
        image.onerror = () => finish(false);
        signal.addEventListener('abort', handleAbort, { once: true });
        image.src = sourceUrl;
    });
}
