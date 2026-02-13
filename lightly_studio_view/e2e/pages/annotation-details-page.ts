import { type Page, expect } from '@playwright/test';

export class AnnotationDetailsPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    waitForNavigation() {
        return this.page.waitForSelector('[data-testid="annotation-navigation"]', {
            state: 'attached'
        });
    }

    getSampleName() {
        return this.page.getByTestId('sample-metadata-filename');
    }

    getSampleHeight() {
        return this.page.getByTestId('sample-metadata-height');
    }

    getSampleWidth() {
        return this.page.getByTestId('sample-metadata-width');
    }

    getSampleFilepath() {
        return this.page.getByTestId('sample-metadata-filepath');
    }

    getAnnotationBoxes() {
        return this.page.getByTestId('annotation_box');
    }

    getAnnotationDeleteButton() {
        return this.page.getByTestId('delete-annotation-trigger');
    }

    getAnnotationConfirmDeleteButton() {
        return this.page.getByTestId('confirm-delete-annotation');
    }

    getAnnotationHeight() {
        return this.page.getByTestId('annotation-metadata-height');
    }

    getAnnotationWidth() {
        return this.page.getByTestId('annotation-metadata-width');
    }

    getNextButton() {
        return this.page.getByRole('button', { name: 'Next sample' });
    }

    getPrevButton() {
        return this.page.getByRole('button', { name: 'Previous sample' });
    }

    async gotoNextAnnotation() {
        await this.getNextButton().click();
    }

    async gotoNextAnnotationByKeyboard() {
        await this.page.keyboard.press('ArrowRight');
    }

    async gotoPrevAnnotation() {
        await this.getPrevButton().click();
    }

    async gotoPrevAnnotationByKeyboard() {
        await this.page.keyboard.press('ArrowLeft');
    }

    getLabel() {
        return this.page.getByTestId('annotation-metadata-label');
    }

    getSvgAnnotationLabel() {
        return this.page.getByTestId('svg-annotation-text');
    }

    async clickEditLabelButton() {
        await this.page.getByTestId('header-editing-mode-button').click();
    }

    async setLabel(label: string) {
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'PUT' &&
                response.url().includes('/annotations') &&
                response.status() === 200
        );

        await this.page.getByTestId('select-list-trigger').click({ clickCount: 1 });
        const input = this.page.getByTestId('select-list-input');
        await input.waitFor({ state: 'visible' });
        await input.fill(label);
        await this.page.getByRole('option', { name: label, exact: true }).click();

        await responsePromise;
    }

    /**
     * Verifies that the current annotation has the expected dimensions.
     *
     * @param width - Expected width in pixels
     * @param height - Expected height in pixels
     *
     * @example
     * await annotationDetailsPage.verifyDimensions(326, 596);
     */
    async verifyDimensions(width: number, height: number): Promise<void> {
        await expect(this.getAnnotationWidth()).toHaveText(`${width}px`);
        await expect(this.getAnnotationHeight()).toHaveText(`${height}px`);
    }

    getTags() {
        return this.page.getByTestId('segment-tag-name');
    }

    async removeTag(tagName: string) {
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'DELETE' &&
                response.url().includes('/tag/') &&
                response.status() === 200
        );

        await this.page.getByTestId(`remove-tag-${tagName}`).click();

        await responsePromise;
    }

    getZoomScale() {
        return this.page.getByTestId('zoom-scale');
    }

    async clickZoomOut() {
        const zoomScale = this.getZoomScale();
        const before = await zoomScale.textContent();
        await this.page.getByTestId('zoom-out-button').click();
        // Wait for D3 zoom transition (300ms) to settle at a new value.
        await expect(zoomScale).not.toHaveText(before!);
        await this.page.waitForTimeout(350);
    }

    async clickZoomReset() {
        await this.page.getByTestId('zoom-reset-button').click();
        // Wait for D3 zoom transition (300ms) to complete.
        await this.page.waitForTimeout(400);
    }

    getAnnotationBox() {
        return this.page.getByTestId('annotation_box').first();
    }

    async getAnnotationBoxCenterX() {
        const box = await this.getAnnotationBox().boundingBox();
        if (!box) {
            throw new Error('Annotation box bounding box is not available');
        }
        return box.x + box.width / 2;
    }

    async dragAnnotationBox(deltaX: number, deltaY: number) {
        const box = await this.getAnnotationBox().boundingBox();
        if (!box) {
            throw new Error('Annotation box bounding box is not available');
        }

        const startX = box.x + box.width / 2;
        const startY = box.y + box.height / 2;

        // Listen for the PUT annotation response before the drag ends.
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'PUT' &&
                response.url().includes('/annotations') &&
                response.status() === 200
        );

        await this.page.mouse.move(startX, startY);
        await this.page.mouse.down();
        await this.page.mouse.move(startX + deltaX, startY + deltaY);
        await this.page.mouse.up();

        // Wait for the annotation update to be persisted and refetched.
        await responsePromise;
        await this.page.waitForLoadState('networkidle');
        // Wait one render frame so Svelte reactive updates (e.g. resetTargetBoundingBox
        // in ZoomableContainer) have propagated after the refetch.
        await this.page.evaluate(() => new Promise((r) => requestAnimationFrame(r)));
    }

    async undoLastAction() {
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'PUT' &&
                response.url().includes('/annotations') &&
                response.status() === 200
        );

        await this.page.getByTestId('header-reverse-action-button').click();

        await responsePromise;
        await this.page.waitForLoadState('networkidle');
    }
}
