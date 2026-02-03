import { expect, type Page } from '@playwright/test';

export class CaptionUtils {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    getCaptionCount() {
        return this.page.getByTestId('caption-field').count();
    }

    getVideoFrameImageCount() {
        return this.page.getByTestId('video-frame-image').count();
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
    async addCaption(addButtonIndex: number = 0) {
        const captionCountBefore = await this.getCaptionCount();
        await this.page.getByTestId('add-caption-button').nth(addButtonIndex).click();
        // Wait until the new caption field appears
        await expect(this.page.getByTestId('caption-field')).toHaveCount(captionCountBefore + 1);
    }

    async addCaptionInCaptionPage(addButtonIndex: number = 0) {
        const captionCountBefore = await this.getCaptionCount();

        const samplesListPromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/api/samples/list') &&
                response.status() === 200
        );

        await this.page.getByTestId('add-caption-button').nth(addButtonIndex).click();
        await samplesListPromise;

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
        const saveButton = captionField.getByTestId('save-caption-button');

        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'PUT' &&
                response.url().includes('/api/collections/') &&
                response.url().includes('/captions/') &&
                response.status() === 200
        );

        await captionInput.fill(text);
        await expect(captionInput).toHaveValue(text);
        await saveButton.click();

        await responsePromise;
    }
}
