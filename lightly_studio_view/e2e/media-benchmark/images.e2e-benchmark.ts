import { expect, test } from '@playwright/test';
import {
    BackendSampler,
    CACHE_STATE,
    REPETITIONS,
    collectMediaNetwork,
    conditionOrder,
    createBenchmarkContext,
    measureLightweightApi,
    rewriteImageUrl,
    summarize,
    summarizeNetwork,
    writeArtifact,
    type ImageCondition
} from './benchmark';

const CONDITIONS: readonly ImageCondition[] = [
    'proxy-original',
    'direct-original',
    'proxy-thumbnail'
];

interface ImageMeasurement {
    condition: ImageCondition;
    repetition: number;
    firstDecodedMs: number;
    visibleGridDecodedMs: number;
    completionTimeline: Array<{ elapsedMs: number; fraction: number }>;
    imageDimensions: Array<{
        index: number;
        naturalWidth: number;
        naturalHeight: number;
        renderedWidth: number;
        renderedHeight: number;
    }>;
    decodedImages: number;
    failures: number;
    lightweightApiMs: number;
    network: ReturnType<typeof summarizeNetwork>;
    requests: ReturnType<typeof collectMediaNetwork>['entries'];
    backend: Awaited<ReturnType<BackendSampler['stop']>>;
}

test('compare visible-grid image decode completion', async ({ browser, request }) => {
    test.setTimeout(20 * 60_000);
    const settingsResponse = await request.get('/api/settings');
    expect(settingsResponse.ok()).toBeTruthy();
    const originalSettings = await settingsResponse.json();
    const updateResponse = await request.post('/api/settings', {
        data: { ...originalSettings, grid_view_thumbnail_quality: 'high' }
    });
    expect(updateResponse.ok()).toBeTruthy();

    const results: ImageMeasurement[] = [];
    const warmContext =
        CACHE_STATE === 'warm' ? await createBenchmarkContext({ browser }) : undefined;
    try {
        for (let repetition = 0; repetition < REPETITIONS; repetition++) {
            for (const condition of conditionOrder(CONDITIONS, repetition)) {
                const context = await createBenchmarkContext({
                    browser,
                    existingContext: warmContext
                });
                const page = await context.newPage();
                await page.route('**/images/sample/**', (route) =>
                    route.continue({ url: rewriteImageUrl(route.request().url(), condition) })
                );
                const network = collectMediaNetwork(page);
                const backend = new BackendSampler();
                backend.start();
                const startedAt = Date.now();
                const apiMeasurement = measureLightweightApi(page);
                await page.goto('/');
                await page.getByTestId('navigation-menu-images').click();
                await expect(page.getByTestId('sample-grid-item').first()).toBeVisible({
                    timeout: 30_000
                });
                const decode = await measureVisibleImageDecode(page, startedAt);
                const lightweightApiMs = await apiMeasurement;
                await network.settle();
                const networkSummary = summarizeNetwork(network.entries);
                assertImageDelivery(condition, networkSummary);
                results.push({
                    condition,
                    repetition,
                    ...decode,
                    lightweightApiMs,
                    network: networkSummary,
                    requests: network.entries,
                    backend: await backend.stop()
                });
                await page.close();
                if (CACHE_STATE === 'cold') await context.close();
            }
        }
    } finally {
        if (warmContext) await warmContext.close();
        await request.post('/api/settings', { data: originalSettings });
    }

    const summary = Object.fromEntries(
        CONDITIONS.map((condition) => {
            const matching = results.filter((result) => result.condition === condition);
            return [
                condition,
                {
                    firstDecodedMs: summarize(matching.map((result) => result.firstDecodedMs)),
                    visibleGridDecodedMs: summarize(
                        matching.map((result) => result.visibleGridDecodedMs)
                    ),
                    lightweightApiMs: summarize(matching.map((result) => result.lightweightApiMs))
                }
            ];
        })
    );
    const outputPath = writeArtifact(
        'images.json',
        { summary, measurements: results },
        browser.version()
    );
    console.log(`LIG-8835 image benchmark: ${outputPath}`);
});

function assertImageDelivery(
    condition: ImageCondition,
    network: ReturnType<typeof summarizeNetwork>
): void {
    if (condition === 'direct-original' && network.storageRequests === 0) {
        throw new Error(
            'Direct image condition did not reach storage. Check the feature flag and S3 inputs.'
        );
    }
    if (
        condition === 'direct-original' &&
        (network.studioBodyResponses > 0 || network.failures > 0)
    ) {
        throw new Error('Direct image delivery failed or recovered through a Studio media body.');
    }
    if (condition !== 'direct-original' && network.storageRequests > 0) {
        throw new Error(`${condition} unexpectedly reached storage.`);
    }
    if (condition !== 'direct-original' && network.studioBodyResponses === 0) {
        throw new Error(`${condition} did not return a Studio media body.`);
    }
}

async function measureVisibleImageDecode(
    page: Parameters<typeof collectMediaNetwork>[0],
    startedAt: number
) {
    return page.evaluate(
        async ({ actionStartedAt }) => {
            await new Promise<void>((resolve) =>
                requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
            );
            const images = [
                ...document.querySelectorAll<HTMLImageElement>(
                    '[data-testid="sample-grid-item"] img'
                )
            ].filter((image) => {
                const rect = image.getBoundingClientRect();
                return (
                    rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < innerHeight
                );
            });
            if (images.length === 0) throw new Error('No visible grid images were found.');
            const completed: number[] = [];
            let failures = 0;
            await Promise.all(
                images.map(async (image) => {
                    try {
                        await image.decode();
                        if (image.naturalWidth === 0)
                            throw new Error('Decoded image has no pixels.');
                    } catch {
                        failures++;
                    } finally {
                        completed.push(Date.now() - actionStartedAt);
                    }
                })
            );
            completed.sort((left, right) => left - right);
            return {
                firstDecodedMs: completed[0],
                visibleGridDecodedMs: completed.at(-1)!,
                completionTimeline: completed.map((elapsedMs, index) => ({
                    elapsedMs,
                    fraction: (index + 1) / images.length
                })),
                imageDimensions: images.map((image, index) => {
                    const rect = image.getBoundingClientRect();
                    return {
                        index,
                        naturalWidth: image.naturalWidth,
                        naturalHeight: image.naturalHeight,
                        renderedWidth: rect.width,
                        renderedHeight: rect.height
                    };
                }),
                decodedImages: images.length - failures,
                failures
            };
        },
        { actionStartedAt: startedAt }
    );
}
