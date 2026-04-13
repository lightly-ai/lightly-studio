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

test('samples grid renders within 5 seconds', async ({ page, samplesPage }) => {
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await page.reload();
        await samplesPage.goto();
        return await measureElementRendering(page, samplesPage.getSampleByIndex(1));
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;

    console.log('samples-grid measurements:', result);

    metrics.push({
        test: 'samples-grid',
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

test('sample details renders within 5 seconds', async ({
    page,
    samplesPage,
    sampleDetailsPage
}) => {
    await samplesPage.goto();

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await samplesPage.goto();
        await samplesPage.doubleClickFirstSample();
        const time = await measureElementRendering(page, sampleDetailsPage.getSampleDetails());
        await page.goBack();
        return time;
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;
    console.log('sample-details measurements:', result);

    metrics.push({
        test: 'sample-details',
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

test('sample details renders next image within 5 seconds', async ({
    page,
    samplesPage,
    sampleDetailsPage
}) => {
    await samplesPage.goto();

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await samplesPage.goto();
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.getSampleDetails().waitFor({ state: 'visible' });
        await sampleDetailsPage.getNextButton().click();
        const time = await measureElementRendering(page, sampleDetailsPage.getSampleDetails());
        return time;
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;
    console.log('sample-details-next-image measurements:', result);

    metrics.push({
        test: 'sample-details-next-image',
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

test('sample details renders prev image within 5 seconds', async ({
    page,
    samplesPage,
    sampleDetailsPage
}) => {
    await samplesPage.goto();

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await samplesPage.goto();
        await samplesPage.getSampleByIndex(1).dblclick();
        await sampleDetailsPage.getSampleDetails().waitFor({ state: 'visible' });
        await sampleDetailsPage.getPrevButton().click();
        const time = await measureElementRendering(page, sampleDetailsPage.getSampleDetails());
        return time;
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;
    console.log('sample-details-prev-image measurements:', result);

    metrics.push({
        test: 'sample-details-prev-image',
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

test('annotations grid renders within 5 seconds', async ({ page, annotationsPage }) => {
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await page.reload();
        await annotationsPage.goto();
        return await measureElementRendering(page, annotationsPage.getAnnotations().nth(1));
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'annotations-grid',
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

test('annotation details renders within 5 seconds', async ({
    page,
    annotationsPage,
    annotationDetailsPage
}) => {
    await annotationsPage.goto();
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureWithMedian(async () => {
        await annotationsPage.goto();
        await annotationsPage.clickAnnotation(0);
        await annotationDetailsPage.waitForNavigation();
        const time = await measureElementRendering(page, annotationDetailsPage.getAnnotationBox());
        await page.goBack();
        return time;
    }, MEASUREMENT_ITERATIONS);

    const passed = result.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'annotation-details',
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
