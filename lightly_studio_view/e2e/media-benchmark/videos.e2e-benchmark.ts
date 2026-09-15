import { expect, test, type Page } from '@playwright/test';
import {
    BackendSampler,
    CACHE_STATE,
    REPETITIONS,
    collectMediaNetwork,
    conditionOrder,
    createBenchmarkContext,
    measureLightweightApi,
    rewriteVideoUrl,
    summarize,
    summarizeNetwork,
    writeArtifact,
    type VideoCondition
} from './benchmark';

const CONDITIONS: readonly VideoCondition[] = ['proxy', 'direct'];

interface VideoMeasurement {
    condition: VideoCondition;
    repetition: number;
    detailsToFirstFrameMs: number;
    playToFirstFrameMs: number;
    seekMs: number;
    seekTargetS: number;
    seekTargetBuffered: boolean;
    resumeMs: number;
    durationS: number;
    videoWidth: number;
    videoHeight: number;
    lightweightApiMs: number;
    network: ReturnType<typeof summarizeNetwork>;
    requests: ReturnType<typeof collectMediaNetwork>['entries'];
    backend: Awaited<ReturnType<BackendSampler['stop']>>;
}

test('compare video first frame, seek, and resume', async ({ browser }) => {
    test.setTimeout(20 * 60_000);
    const results: VideoMeasurement[] = [];
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
                await page.route('**/videos/media/**', (route) =>
                    route.continue({ url: rewriteVideoUrl(route.request().url(), condition) })
                );
                const network = collectMediaNetwork(page);
                const backend = new BackendSampler();
                backend.start();
                await page.goto('/');
                await page.getByTestId('navigation-menu-videos').click();
                const firstVideo = page.getByTestId('video-grid-item').first();
                await expect(firstVideo).toBeVisible({ timeout: 30_000 });
                const detailsStartedAt = Date.now();
                const apiMeasurement = measureLightweightApi(page);
                await firstVideo.dblclick();
                const video = page.getByRole('region', { name: 'Video player' }).locator('video');
                await expect(video).toBeVisible({ timeout: 30_000 });
                const playback = await measureVideoPlayback(page, detailsStartedAt);
                const lightweightApiMs = await apiMeasurement;
                await network.settle();
                const networkSummary = summarizeNetwork(network.entries);
                assertVideoDelivery(condition, networkSummary);
                results.push({
                    condition,
                    repetition,
                    ...playback,
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
    }

    const summary = Object.fromEntries(
        CONDITIONS.map((condition) => {
            const matching = results.filter((result) => result.condition === condition);
            return [
                condition,
                {
                    detailsToFirstFrameMs: summarize(
                        matching.map((result) => result.detailsToFirstFrameMs)
                    ),
                    playToFirstFrameMs: summarize(
                        matching.map((result) => result.playToFirstFrameMs)
                    ),
                    seekMs: summarize(matching.map((result) => result.seekMs)),
                    resumeMs: summarize(matching.map((result) => result.resumeMs)),
                    lightweightApiMs: summarize(matching.map((result) => result.lightweightApiMs))
                }
            ];
        })
    );
    const outputPath = writeArtifact(
        'videos.json',
        { summary, measurements: results },
        browser.version()
    );
    console.log(`LIG-8835 video benchmark: ${outputPath}`);
});

function assertVideoDelivery(
    condition: VideoCondition,
    network: ReturnType<typeof summarizeNetwork>
): void {
    if (condition === 'direct' && network.storageBodyResponses === 0) {
        throw new Error(
            'Direct video condition did not receive a storage media body. Check the feature flag and S3 inputs.'
        );
    }
    if (condition === 'direct' && network.studioBodyResponses > 0) {
        throw new Error('Direct video delivery recovered through a Studio media body.');
    }
    if (condition === 'proxy' && network.storageRequests > 0) {
        throw new Error('Proxy video condition unexpectedly reached storage.');
    }
    if (condition === 'proxy' && network.studioBodyResponses === 0) {
        throw new Error('Proxy video condition did not return a Studio media body.');
    }
}

async function measureVideoPlayback(page: Page, detailsStartedAt: number) {
    return page
        .getByRole('region', { name: 'Video player' })
        .locator('video')
        .evaluate(async (video, actionStartedAt) => {
            const presentedFrame = () =>
                new Promise<void>((resolve) => {
                    if ('requestVideoFrameCallback' in video)
                        video.requestVideoFrameCallback(() => resolve());
                    else video.addEventListener('timeupdate', () => resolve(), { once: true });
                });
            if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
                await new Promise<void>((resolve, reject) => {
                    video.addEventListener('loadedmetadata', () => resolve(), { once: true });
                    video.addEventListener('error', () => reject(video.error), { once: true });
                });
            }
            if (!Number.isFinite(video.duration) || video.duration <= 0) {
                throw new Error(`The benchmark video has invalid duration ${video.duration}.`);
            }
            const playStartedAt = performance.now();
            const firstFrame = presentedFrame();
            await video.play();
            await firstFrame;
            const firstFrameAt = performance.now();
            const target = Math.max(0, Math.min(video.duration * 0.75, video.duration - 0.25));
            const buffered = [...Array(video.buffered.length).keys()].some(
                (index) =>
                    video.buffered.start(index) <= target && video.buffered.end(index) >= target
            );
            const seekStartedAt = performance.now();
            video.currentTime = target;
            await new Promise<void>((resolve) =>
                video.addEventListener('seeked', () => resolve(), { once: true })
            );
            const seekFrame = presentedFrame();
            await seekFrame;
            const seekFinishedAt = performance.now();
            video.pause();
            const resumeStartedAt = performance.now();
            const resumedFrame = presentedFrame();
            await video.play();
            await resumedFrame;
            return {
                detailsToFirstFrameMs: Date.now() - actionStartedAt,
                playToFirstFrameMs: firstFrameAt - playStartedAt,
                seekMs: seekFinishedAt - seekStartedAt,
                seekTargetS: target,
                seekTargetBuffered: buffered,
                resumeMs: performance.now() - resumeStartedAt,
                durationS: video.duration,
                videoWidth: video.videoWidth,
                videoHeight: video.videoHeight
            };
        }, detailsStartedAt);
}
