import {
    expectWithinPerformanceLimits,
    isWithinPerformanceLimits,
    measureElementRendering,
    measureMemoryConsumption,
    measureRenderAndMemory,
    setNetworkThrottling,
    test
} from '../utils';
import { VideoFramesPage, VideosPage } from '../pages';
import * as fs from 'fs';
import * as path from 'path';

const PERFORMANCE_LIMITS = {
    maxRenderTimeMs: 5000,
    maxMemoryUsageMb: 256
};
const MEASUREMENT_ITERATIONS = 5;
type MeasurementSummary = Awaited<ReturnType<typeof measureRenderAndMemory>>['memoryUsageMb'];

const metrics: Array<{
    test: string;
    measurements: number[];
    median: number;
    min: number;
    max: number;
    average: number;
    memoryUsageMb: MeasurementSummary;
    passed: boolean;
}> = [];

function saveMetrics() {
    if (process.env.CI) {
        const metricsPath = path.join(process.cwd(), 'performance-metrics.json');
        fs.writeFileSync(metricsPath, JSON.stringify(metrics, null, 2));
    }
}

test('videos grid renders within 5 seconds', async ({ page }) => {
    const videosPage = new VideosPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await videosPage.goto();
        const renderTimeMs = await measureElementRendering(page, videosPage.getVideoByIndex(1));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);

    metrics.push({
        test: 'videos-grid',
        measurements: result.renderTimeMs.measurements,
        median: result.renderTimeMs.median,
        min: result.renderTimeMs.min,
        max: result.renderTimeMs.max,
        average: result.renderTimeMs.average,
        memoryUsageMb: result.memoryUsageMb,
        passed
    });
    saveMetrics();

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('video frames grid renders within 5 seconds', async ({ page }) => {
    const videoFramesPage = new VideoFramesPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await videoFramesPage.goto();
        const renderTimeMs = await measureElementRendering(
            page,
            videoFramesPage.getVideoFrameByIndex(1)
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);

    metrics.push({
        test: 'video-frames-grid',
        measurements: result.renderTimeMs.measurements,
        median: result.renderTimeMs.median,
        min: result.renderTimeMs.min,
        max: result.renderTimeMs.max,
        average: result.renderTimeMs.average,
        memoryUsageMb: result.memoryUsageMb,
        passed
    });
    saveMetrics();

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('video frame details renders within 5 seconds', async ({ page }) => {
    const videoFramesPage = new VideoFramesPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await videoFramesPage.goto();
        await videoFramesPage.doubleClickFirstVideoFrame();
        const renderTimeMs = await measureElementRendering(
            page,
            videoFramesPage.getSampleDetails()
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        await page.goBack();
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);

    metrics.push({
        test: 'video-frame-details',
        measurements: result.renderTimeMs.measurements,
        median: result.renderTimeMs.median,
        min: result.renderTimeMs.min,
        max: result.renderTimeMs.max,
        average: result.renderTimeMs.average,
        memoryUsageMb: result.memoryUsageMb,
        passed
    });
    saveMetrics();

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('video details renders within 5 seconds', async ({ page }) => {
    const videosPage = new VideosPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await videosPage.goto();
        await videosPage.getVideoByIndex(0).dblclick();
        const renderTimeMs = await measureElementRendering(
            page,
            page.getByTestId('video-file-name')
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        await page.goBack();
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);

    metrics.push({
        test: 'video-details',
        measurements: result.renderTimeMs.measurements,
        median: result.renderTimeMs.median,
        min: result.renderTimeMs.min,
        max: result.renderTimeMs.max,
        average: result.renderTimeMs.average,
        memoryUsageMb: result.memoryUsageMb,
        passed
    });
    saveMetrics();

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});
