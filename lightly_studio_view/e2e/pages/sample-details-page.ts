import { expect, type Page } from '@playwright/test';

export class SampleDetailsPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    async pageIsReady() {
        await expect(this.getSampleDetails()).toBeVisible();
    }

    getSampleDetails() {
        return this.page.getByTestId('sample-details');
    }

    getLabelSelects() {
        return this.page.getByTestId('select-list-trigger');
    }

    getLabelInputs() {
        return this.page.getByTestId('select-list-input');
    }

    getSampleName() {
        return this.page.getByTestId('sample-metadata-filename');
    }

    getAnnotationBoxes() {
        return this.page.getByTestId('annotation_box');
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

    async gotoNextSampleByKeyboard() {
        await this.page.keyboard.press('ArrowRight');
    }

    async gotoPrevAnnotation() {
        await this.getPrevButton().click();
    }

    async gotoPrevAnnotationByKeyboard() {
        await this.page.keyboard.press('ArrowLeft');
    }

    async clickEditButton() {
        await this.page.getByTestId('header-editing-mode-button').click();
    }

    async hasAnnotationWithLabel(label: string) {
        return this.page.getByLabel(label).isVisible();
    }

    getAnnotationBoxByLabel(label: string) {
        return this.page.locator(`[data-testid="selectable-svg-group"] [data-label="${label}"]`);
    }

    async setLabel(label: string) {
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'PUT' &&
                response.url().includes('/annotations') &&
                response.status() === 200
        );

        await this.page.getByTestId('select-list-input').fill(label);
        await this.page.getByRole('option', { name: label, exact: true }).click();
        await this.pageIsReady();

        await responsePromise;
    }

    async setFirstAnnotationLabel(label: string) {
        await this.getLabelSelects().first().click();
        await this.setLabel(label);
    }
}
