import {
    expect,
    measureElementRendering,
    measureMemoryConsumption,
    measureRenderAndMemory,
    type MeasurementSummary,
    setNetworkThrottling,
    test
} from '../utils';
import * as fs from 'fs';
import * as path from 'path';

const MAX_RENDER_TIME_MS = 5000;
const MEASUREMENT_ITERATIONS = 5;

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

test('videos grid renders within 5 seconds', async ({ page, videosPage }) => {
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await page.reload();
        await videosPage.goto();
        const renderTimeMs = await measureElementRendering(page, videosPage.getVideoByIndex(1));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;

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

    expect(result.renderTimeMs.median).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video frames grid renders within 5 seconds', async ({ page, videoFramesPage }) => {
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await page.reload();
        await videoFramesPage.goto();
        const renderTimeMs = await measureElementRendering(
            page,
            videoFramesPage.getVideoFrameByIndex(1)
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;

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

    expect(result.renderTimeMs.median).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video frame details renders within 5 seconds', async ({ page, videoFramesPage }) => {
    await videoFramesPage.goto();
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

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;

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

    expect(result.renderTimeMs.median).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video details renders within 5 seconds', async ({ page, videosPage }) => {
    await videosPage.goto();
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

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;

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

    expect(result.renderTimeMs.median).toBeLessThan(MAX_RENDER_TIME_MS);
});
