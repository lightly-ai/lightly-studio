import { type Page, expect } from '@playwright/test';
import { CaptionUtils } from '../caption-utils';

export class CaptionsPage {
    private captionUtils: CaptionUtils;

    constructor(public readonly page: Page) {
        this.page = page;
        this.captionUtils = new CaptionUtils(page);
    }

    async goto() {
        await this.page.goto('/');
        await expect(this.page.getByTestId('sample-grid-item').first()).toBeVisible();
        await this.page.getByTestId('navigation-menu-captions').click();
        // Wait for the captions grid to be visible
        await expect(this.getNthGridItem(0)).toBeVisible();
    }

    async gotoVideoFrameCaptions() {
        await this.page.goto('/');

        await this.page.getByTestId('navigation-menu-frames').hover();
        await this.page.getByTestId('navigation-menu-captions').click();

        // Wait for the captions grid to be visible
        await expect(this.getNthGridItem(0)).toBeVisible();
    }

    async clickEditButton() {
        await this.page.getByTestId('header-editing-mode-button').click();
    }

    getGridItemCount() {
        return this.page.getByTestId('caption-grid-item').count();
    }

    getNthGridItem(index: number) {
        return this.page.getByTestId('caption-grid-item').nth(index);
    }

    getCaptionCount() {
        return this.captionUtils.getCaptionCount();
    }

    getVideoFrameImageCount() {
        return this.captionUtils.getVideoFrameImageCount();
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

    async addCaption(addButtonIndex: number) {
        await this.captionUtils.addCaption(addButtonIndex);
    }

    async deleteNthCaption(index: number) {
        await this.captionUtils.deleteNthCaption(index);
    }

    async updateNthCaption(index: number, text: string) {
        await this.captionUtils.updateNthCaption(index, text);
    }
}
