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

    // DRAFT

    // TODO(Michal, 12/2025): Change the function signature once it is not possible to
    // add a caption without text.
    async addCaption() {
        const captionCountBefore = await this.getCaptionCount();

        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/captions') &&
                response.status() === 200
        );

        
        await this.page.getByTestId('add-caption-button').click();
        await responsePromise;
        // Wait for one second for the UI to update
        await expect(this.page.getByTestId('caption-field')).toHaveCount(captionCountBefore + 1);
    }

    async updateNthCaption(index: number, text: string) {
        const captionField = this.getNthCaption(index);
        const captionInput = captionField.getByTestId('caption-input');
        await captionInput.fill(text);
        await captionField.getByTestId('save-caption-button').click();
    }

    async deleteNthCaption(index: number) {
        // TODO

        caption = this.getNthCaption(index);
        await caption.getByTestId('delete-caption-button').click();
    }

    getCaptionCount() {
        return this.page.getByTestId('caption-field').count();
    }

    getNthCaption(index: number) {
        return this.page.getByTestId('caption-field').nth(index);
    }
}
