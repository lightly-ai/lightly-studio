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

test('samples grid renders within 5 seconds', async ({ page, samplesPage }) => {
    await setNetworkThrottling(page, 'Fast4G');
    await samplesPage.goto();

    const paintTime = await measureElementRendering(page, samplesPage.getSampleByIndex(1));
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'samples-grid', renderTime: paintTime, passed });
    saveMetrics();

    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('sample details renders within 5 seconds', async ({
    page,
    samplesPage,
    sampleDetailsPage
}) => {
    await samplesPage.goto();
    await samplesPage.doubleClickFirstSample();
    await setNetworkThrottling(page, 'Fast4G');

    const paintTime = await measureElementRendering(page, sampleDetailsPage.getSampleDetails());
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'sample-details', renderTime: paintTime, passed });
    saveMetrics();

    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('annotations grid renders within 5 seconds', async ({ page, annotationsPage }) => {
    await setNetworkThrottling(page, 'Fast4G');
    await annotationsPage.goto();

    const paintTime = await measureElementRendering(page, annotationsPage.getAnnotations().nth(1));
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'annotations-grid', renderTime: paintTime, passed });
    saveMetrics();

    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});

test('annotation details renders within 5 seconds', async ({
    page,
    annotationsPage,
    annotationDetailsPage
}) => {
    await annotationsPage.goto();
    await setNetworkThrottling(page, 'Fast4G');
    await annotationsPage.clickAnnotation(0);
    await annotationDetailsPage.waitForNavigation();

    const paintTime = await measureElementRendering(page, annotationDetailsPage.getAnnotationBox());
    const passed = paintTime < MAX_RENDER_TIME_MS;

    metrics.push({ test: 'annotation-details', renderTime: paintTime, passed });
    saveMetrics();
    expect(paintTime).toBeLessThan(MAX_RENDER_TIME_MS);
});
