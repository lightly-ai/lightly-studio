import { type Page, expect } from '@playwright/test';
import { CaptionUtils } from '../caption-utils';

export class CaptionsPage {
    private captionUtils: CaptionUtils;

    constructor(public readonly page: Page) {
        this.page = page;
        this.captionUtils = new CaptionUtils(page);
    }

    /**
     * Navigates to the captions page via the navigation menu.
     *
     * The sidebar lists every collection of the dataset as its own row, so the captions view
     * is one click away rather than a breadcrumb level to expand.
     */
    async goto() {
        await this.page.goto('/');
        await this.page.getByTestId('navigation-menu-captions').click();

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

    async addCaptionInCaptionPage(addButtonIndex: number) {
        await this.captionUtils.addCaptionInCaptionPage(addButtonIndex);
    }

    async deleteNthCaption(index: number) {
        await this.captionUtils.deleteNthCaption(index);
    }

    async undoLastCaptionDelete() {
        await this.captionUtils.undoLastCaptionDelete();
    }

    async updateNthCaption(index: number, text: string) {
        await this.captionUtils.updateNthCaption(index, text);
    }
}
