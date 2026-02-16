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

    getNthCaptionText(index: number) {
        return this.getNthCaption(index).textContent();
    }

    getNthCaptionInput(index: number) {
        return this.getNthCaption(index).getByTestId('caption-input').inputValue();
    }

    async addCaption(addButtonIndex: number = 0, text: string = 'new caption') {
        const captionCountBefore = await this.getCaptionCount();
        await this.page.getByTestId('add-caption-button').nth(addButtonIndex).click();
        const newCaptionInput = this.page.getByTestId('new-caption-input').nth(0);
        await expect(newCaptionInput).toBeVisible();
        await newCaptionInput.fill(text);
        await newCaptionInput.press('Enter');
        await expect(this.page.getByTestId('caption-field')).toHaveCount(captionCountBefore + 1);
    }

    async addCaptionInCaptionPage(addButtonIndex: number = 0, text: string = 'new caption') {
        await this.addCaption(addButtonIndex, text);
    }

    async deleteNthCaption(index: number) {
        const captionField = this.getNthCaption(index);
        await expect(captionField).toBeVisible();

        const captionCountBefore = await this.getCaptionCount();
        await captionField.getByTestId('delete-caption-button').click();
        await this.page.getByTestId('confirm-delete-caption-button').click();
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
