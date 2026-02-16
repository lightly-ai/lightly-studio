import { expect, type Page } from '@playwright/test';
import { CaptionUtils } from '../caption-utils';

export class VideoFrameDetailsPage {
    private captionUtils: CaptionUtils;

    constructor(public readonly page: Page) {
        this.page = page;
        this.captionUtils = new CaptionUtils(page);
    }

    async pageIsReady() {
        await expect(this.getSampleDetails()).toBeVisible();
    }

    getSampleDetails() {
        return this.page.getByTestId('video-frame-details');
    }

    async clickEditButton() {
        await this.page.getByTestId('header-editing-mode-button').click();
    }

    async getFrameNumber() {
        const frameNumberText = await this.page
            .locator('xpath=//span[text()="Number:"]/following-sibling::span[1]')
            .textContent();

        return frameNumberText?.trim() ?? '';
    }

    async getFrameTimestamp() {
        const frameTimestampText = await this.page
            .locator('xpath=//span[text()="Timestamp:"]/following-sibling::span[1]')
            .textContent();

        return frameTimestampText?.trim() ?? '';
    }

    // Captions

    getCaptionCount() {
        return this.captionUtils.getCaptionCount();
    }

    getNthCaption(index: number) {
        return this.captionUtils.getNthCaption(index);
    }

    getNthCaptionText(index: number) {
        return this.captionUtils.getNthCaptionText(index);
    }

    getNthCaptionInput(index: number) {
        return this.captionUtils.getNthCaptionInput(index);
    }

    async addCaption() {
        await this.captionUtils.addCaption();
    }

    async deleteNthCaption(index: number) {
        await this.captionUtils.deleteNthCaption(index);
    }

    async updateNthCaption(index: number, text: string) {
        await this.captionUtils.updateNthCaption(index, text);
    }
}
