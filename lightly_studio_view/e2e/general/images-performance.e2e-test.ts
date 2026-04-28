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

test('samples grid renders within 5 seconds', async ({ page, samplesPage }) => {
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await page.reload();
        await samplesPage.goto();
        const renderTimeMs = await measureElementRendering(page, samplesPage.getSampleByIndex(1));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;

    console.log('samples-grid measurements:', result);

    metrics.push({
        test: 'samples-grid',
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

test('sample details renders within 5 seconds', async ({ page, samplesPage }) => {
    await samplesPage.goto();

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await samplesPage.goto();
        await samplesPage.doubleClickFirstSample();
        const renderTimeMs = await measureElementRendering(page, page.getByText('Sample 1 of 128'));
        const memoryUsageMb = await measureMemoryConsumption(page);
        await page.goBack();
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;
    console.log('sample-details measurements:', result);

    metrics.push({
        test: 'sample-details',
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

test('sample details renders next image within 5 seconds', async ({
    page,
    samplesPage,
    sampleDetailsPage
}) => {
    await samplesPage.goto();

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await samplesPage.goto();
        await samplesPage.doubleClickFirstSample();

        await page.getByText('Sample 1 of 128').waitFor();
        await sampleDetailsPage.getNextButton().click();
        const renderTimeMs = await measureElementRendering(page, page.getByText('Sample 2 of 128'));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;
    console.log('sample-details-next-image measurements:', result);

    metrics.push({
        test: 'sample-details-next-image',
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

test('sample details renders prev image within 5 seconds', async ({
    page,
    samplesPage,
    sampleDetailsPage
}) => {
    await samplesPage.goto();

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await samplesPage.goto();
        await samplesPage.getSampleByIndex(1).dblclick();
        await page.getByText('Sample 2 of 128').waitFor({ state: 'visible' });
        await sampleDetailsPage.getPrevButton().click();
        const renderTimeMs = await measureElementRendering(page, page.getByText('Sample 1 of 128'));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;
    console.log('sample-details-prev-image measurements:', result);

    metrics.push({
        test: 'sample-details-prev-image',
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

test('annotations grid renders within 5 seconds', async ({ page, annotationsPage }) => {
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await page.reload();
        await annotationsPage.goto();
        const renderTimeMs = await measureElementRendering(
            page,
            annotationsPage.getAnnotations().nth(1)
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'annotations-grid',
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

test('annotation details renders within 5 seconds', async ({
    page,
    annotationsPage,
    annotationDetailsPage
}) => {
    await annotationsPage.goto();
    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await annotationsPage.goto();
        await annotationsPage.clickAnnotation(0);
        await annotationDetailsPage.waitForNavigation();
        const renderTimeMs = await measureElementRendering(
            page,
            annotationDetailsPage.getAnnotationBox()
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        await page.goBack();
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = result.renderTimeMs.median < MAX_RENDER_TIME_MS;

    metrics.push({
        test: 'annotation-details',
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
