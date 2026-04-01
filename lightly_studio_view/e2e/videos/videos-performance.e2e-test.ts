import {
    expect,
    measureElementRendering,
    measureWithMedian,
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

    const result = await measureWithMedian(async () => {
        await page.reload();
        await videosPage.goto();
        return await measureElementRendering(page, videosPage.getVideoByIndex(1));
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'videos-grid',
        measurements: result.measurements,
        median: result.median,
        min: result.min,
        max: result.max,
        average: result.average,
        passed
    });
    saveMetrics();

    expect(result.median).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video frames grid renders within 5 seconds', async ({ page, videoFramesPage }) => {
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await page.reload();
        await videoFramesPage.goto();
        return await measureElementRendering(page, videoFramesPage.getVideoFrameByIndex(1));
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'video-frames-grid',
        measurements: result.measurements,
        median: result.median,
        min: result.min,
        max: result.max,
        average: result.average,
        passed
    });
    saveMetrics();

    expect(result.median).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video frame details renders within 5 seconds', async ({ page, videoFramesPage }) => {
    await videoFramesPage.goto();
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await videoFramesPage.goto();
        await videoFramesPage.doubleClickFirstVideoFrame();
        const time = await measureElementRendering(page, videoFramesPage.getSampleDetails());
        await page.goBack();
        return time;
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'video-frame-details',
        measurements: result.measurements,
        median: result.median,
        min: result.min,
        max: result.max,
        average: result.average,
        passed
    });
    saveMetrics();

    expect(result.median).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video details renders within 5 seconds', async ({ page, videosPage }) => {
    await videosPage.goto();
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await videosPage.goto();
        await videosPage.getVideoByIndex(0).dblclick();
        const time = await measureElementRendering(page, page.getByTestId('video-file-name'));
        await page.goBack();
        return time;
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'video-details',
        measurements: result.measurements,
        median: result.median,
        min: result.min,
        max: result.max,
        average: result.average,
        passed
    });
    saveMetrics();

    expect(result.median).toBeLessThan(MAX_RENDER_TIME_MS);
});
