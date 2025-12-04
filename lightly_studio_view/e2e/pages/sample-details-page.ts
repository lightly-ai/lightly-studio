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

    // Captions

    getCaptionCount() {
        return this.page.getByTestId('caption-field').count();
    }

    getNthCaption(index: number) {
        return this.page.getByTestId('caption-field').nth(index);
    }

    // Get text content of the nth caption. Useful for checking the caption in view mode.
    getNthCaptionText(index: number) {
        return this.getNthCaption(index).textContent();
    }

    // Get input value of the nth caption. Useful for checking the caption in edit mode.
    getNthCaptionInput(index: number) {
        return this.getNthCaption(index).getByTestId('caption-input').inputValue();
    }

    // TODO(Michal, 12/2025): Change the function signature once it is not possible to
    // add a caption without text.
    async addCaption() {
        const captionCountBefore = await this.getCaptionCount();
        await this.page.getByTestId('add-caption-button').click();
        // Wait until the new caption field appears
        await expect(this.page.getByTestId('caption-field')).toHaveCount(captionCountBefore + 1);
    }

    async deleteNthCaption(index: number) {
        // Ensure the caption exists
        const captionField = this.getNthCaption(index);
        await expect(captionField).toBeVisible();

        // Get the caption count before deletion
        const captionCountBefore = await this.getCaptionCount();

        // Click the delete button
        await captionField.getByTestId('delete-caption-button').click();

        // Confirm deletion. Note that the popover is portalled, it is not inside the caption field.
        await this.page.getByTestId('confirm-delete-caption-button').click();

        // Wait until the caption field is removed
        await expect(this.page.getByTestId('caption-field')).toHaveCount(captionCountBefore - 1);
    }

    async updateNthCaption(index: number, text: string) {
        const captionField = this.getNthCaption(index);
        const captionInput = captionField.getByTestId('caption-input');
        await captionInput.fill(text);
        await captionField.getByTestId('save-caption-button').click();
    }
}
