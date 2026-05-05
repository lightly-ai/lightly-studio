import {
    expectWithinPerformanceLimits,
    isWithinPerformanceLimits,
    measureElementRendering,
    measureMemoryConsumption,
    measureRenderAndMemory,
    setNetworkThrottling,
    test
} from '../utils';
import { AnnotationDetailsPage, AnnotationsPage, SampleDetailsPage, SamplesPage } from '../pages';
import * as fs from 'fs';
import * as path from 'path';

const PERFORMANCE_LIMITS = {
    maxRenderTimeMs: 6000,
    maxMemoryUsageMb: 256
};
const MEASUREMENT_ITERATIONS = 3;
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

test('samples grid renders within 5 seconds', async ({ page }) => {
    const samplesPage = new SamplesPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await samplesPage.goto();
        const renderTimeMs = await measureElementRendering(page, samplesPage.getSampleByIndex(1));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);

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
    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('sample details renders within 5 seconds', async ({ page }) => {
    const samplesPage = new SamplesPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await samplesPage.goto();
        await samplesPage.doubleClickFirstSample();
        const renderTimeMs = await measureElementRendering(page, page.getByText('Sample 1 of 128'));
        const memoryUsageMb = await measureMemoryConsumption(page);
        await page.goBack();
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
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

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('sample details renders next image within 5 seconds', async ({ page }) => {
    const samplesPage = new SamplesPage(page);
    const sampleDetailsPage = new SampleDetailsPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await samplesPage.goto();
        await samplesPage.doubleClickFirstSample();

        await page.getByText('Sample 1 of 128').waitFor({ state: 'visible', timeout: 10000 });
        await sampleDetailsPage.getNextButton().click();
        const renderTimeMs = await measureElementRendering(page, page.getByText('Sample 2 of 128'));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
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

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('sample details renders prev image within 5 seconds', async ({ page }) => {
    const samplesPage = new SamplesPage(page);
    const sampleDetailsPage = new SampleDetailsPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await samplesPage.goto();
        await samplesPage.doubleClickNthSample(1);
        await page.getByText('Sample 2 of 128').waitFor({ state: 'visible', timeout: 10000 });
        await sampleDetailsPage.getPrevButton().click();
        const renderTimeMs = await measureElementRendering(page, page.getByText('Sample 1 of 128'));
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
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

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('annotations grid renders within 5 seconds', async ({ page }) => {
    const annotationsPage = new AnnotationsPage(page);

    await setNetworkThrottling(page, 'Fast4G');

    const result = await measureRenderAndMemory(async () => {
        await annotationsPage.goto();
        const renderTimeMs = await measureElementRendering(
            page,
            annotationsPage.getAnnotations().nth(1)
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);

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

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});

test('annotation details renders within 5 seconds', async ({ page }) => {
    const annotationsPage = new AnnotationsPage(page);
    const annotationDetailsPage = new AnnotationDetailsPage(page);

    await setNetworkThrottling(page, 'Fast4G');
    await annotationsPage.goto();
    const annotationsUrl = page.url();

    const result = await measureRenderAndMemory(async () => {
        await page.goto(annotationsUrl);
        await annotationsPage
            .getAnnotations()
            .first()
            .waitFor({ state: 'visible', timeout: 10000 });
        await annotationsPage.clickAnnotation(0);
        await annotationDetailsPage.waitForNavigation();
        const renderTimeMs = await measureElementRendering(
            page,
            annotationDetailsPage.getAnnotationBox()
        );
        const memoryUsageMb = await measureMemoryConsumption(page);
        return { renderTimeMs, memoryUsageMb };
    }, MEASUREMENT_ITERATIONS);

    const passed = isWithinPerformanceLimits(result, PERFORMANCE_LIMITS);

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

    expectWithinPerformanceLimits(result, PERFORMANCE_LIMITS);
});
