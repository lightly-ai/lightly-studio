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

    getAnnotationDeleteAnnotationTrigger() {
        return this.page.getByTestId('delete-annotation-trigger');
    }

    getAnnotationConfirmDeleteAnnotation() {
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
}
