import { test, expect } from '@playwright/test';
import { measureElementRendering } from '../utils';

test.describe('measureElementRendering', () => {
    test('should measure rendering time of a visible element', async ({ page }) => {
        await page.setContent(`
            <div data-testid="test-element" style="width: 100px; height: 100px; background: red;">
                Test Element
            </div>
        `);

        const locator = page.getByTestId('test-element');
        const renderTime = await measureElementRendering(page, locator);

        expect(renderTime).toBeGreaterThan(0);
        expect(typeof renderTime).toBe('number');
    });

    test('should throw error if element does not have data-testid', async ({ page }) => {
        await page.setContent(`
            <div id="test-element" style="width: 100px; height: 100px; background: red;">
                Test Element
            </div>
        `);

        const locator = page.locator('#test-element');

        await expect(measureElementRendering(page, locator)).rejects.toThrow(
            'Element must have a data-testid attribute for performance measurement'
        );
    });

    test('should wait for element to be attached', async ({ page }) => {
        await page.setContent('<div id="container"></div>');

        setTimeout(() => {
            page.evaluate(() => {
                const container = document.getElementById('container');
                const element = document.createElement('div');
                element.setAttribute('data-testid', 'delayed-element');
                element.style.width = '100px';
                element.style.height = '100px';
                element.style.background = 'blue';
                container?.appendChild(element);
            });
        }, 500);

        const locator = page.getByTestId('delayed-element');
        const renderTime = await measureElementRendering(page, locator);

        expect(renderTime).toBeGreaterThan(0);
    });

    test('should detect element visibility with IntersectionObserver', async ({ page }) => {
        await page.setContent(`
            <div style="height: 2000px;">Spacer</div>
            <div data-testid="below-fold" style="width: 100px; height: 100px; background: green;">
                Below Fold
            </div>
        `);

        const locator = page.getByTestId('below-fold');

        const measurePromise = measureElementRendering(page, locator);

        await page.evaluate(() => {
            window.scrollTo(0, document.body.scrollHeight);
        });

        const renderTime = await measurePromise;

        expect(renderTime).toBeGreaterThan(0);
    });

    test('should handle element that does not exist in DOM after attachment', async ({ page }) => {
        await page.setContent(`
            <div data-testid="test-element" style="width: 100px; height: 100px; background: red;">
                Test Element
            </div>
        `);

        const locator = page.getByTestId('test-element');

        await page.evaluate(() => {
            const element = document.querySelector('[data-testid="test-element"]');
            element?.remove();
        });

        const renderTime = await measureElementRendering(page, locator);

        expect(renderTime).toBeGreaterThan(0);
    });

    test('should measure element that is immediately visible', async ({ page }) => {
        await page.setContent(`
            <div data-testid="visible-element" style="width: 100px; height: 100px; background: purple;">
                Visible Element
            </div>
        `);

        const locator = page.getByTestId('visible-element');
        const startTime = await page.evaluate(() => performance.now());
        const renderTime = await measureElementRendering(page, locator);

        expect(renderTime).toBeGreaterThanOrEqual(startTime);
    });

    test('should respect 10% visibility threshold', async ({ page }) => {
        await page.setViewportSize({ width: 800, height: 600 });

        await page.setContent(`
            <div style="height: 2000px;">Spacer</div>
            <div data-testid="partial-element" style="width: 100px; height: 100px; background: orange;">
                Partial Element
            </div>
        `);

        const locator = page.getByTestId('partial-element');

        const measurePromise = measureElementRendering(page, locator);

        await page.evaluate(() => {
            const element = document.querySelector('[data-testid="partial-element"]');
            if (element) {
                const rect = element.getBoundingClientRect();
                window.scrollTo(
                    0,
                    window.scrollY + rect.top - window.innerHeight + rect.height * 0.15
                );
            }
        });

        const renderTime = await measurePromise;

        expect(renderTime).toBeGreaterThan(0);
    });
});
