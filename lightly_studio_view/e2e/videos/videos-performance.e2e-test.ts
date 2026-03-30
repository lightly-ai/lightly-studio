import { expect, measureElementRendering, setNetworkThrottling, test } from '../utils';
import * as fs from 'fs';
import * as path from 'path';

const MAX_RENDER_TIME_MS = 5000;

const metrics: Array<{ test: string; renderTime: number; passed: boolean }> = [];

function saveMetrics() {
    if (process.env.CI) {
        const metricsPath = path.join(process.cwd(), 'performance-metrics.json');
        fs.writeFileSync(metricsPath, JSON.stringify(metrics, null, 2));
    }
}

test('videos grid renders within 5 seconds', async ({ page, videosPage }) => {
    await setNetworkThrottling(page, 'Fast4G');
    await videosPage.goto();

    const paintTime = await measureElementRendering(page, videosPage.getVideoByIndex(1));
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'videos-grid', renderTime: paintTime, passed });
    saveMetrics();

    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video frames grid renders within 5 seconds', async ({ page, videoFramesPage }) => {
    await setNetworkThrottling(page, 'Fast4G');
    await videoFramesPage.goto();

    const paintTime = await measureElementRendering(page, videoFramesPage.getVideoFrameByIndex(1));
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'video-frames-grid', renderTime: paintTime, passed });
    saveMetrics();

    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video frame details renders within 5 seconds', async ({ page, videoFramesPage }) => {
    await videoFramesPage.goto();
    await setNetworkThrottling(page, 'Fast4G');
    await videoFramesPage.doubleClickFirstVideoFrame();

    const paintTime = await measureElementRendering(page, videoFramesPage.getSampleDetails());
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'video-frame-details', renderTime: paintTime, passed });
    saveMetrics();

    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('video details renders within 5 seconds', async ({ page, videosPage }) => {
    await videosPage.goto();
    await setNetworkThrottling(page, 'Fast4G');
    await videosPage.getVideoByIndex(0).dblclick();

    const paintTime = await measureElementRendering(page, page.getByTestId('video-file-name'));
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'video-details', renderTime: paintTime, passed });
    saveMetrics();

    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});
