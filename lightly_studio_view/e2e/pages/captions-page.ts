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
     * A breadcrumb level without siblings renders as an <a> link and clicking
     * navigates directly; a level with siblings renders as a Select trigger
     * (button) and clicking opens a dropdown to pick from.
     *
     * @param menuLevel - Zero-based index of the menu button to interact with.
     */
    async goto(menuLevel: number = 1) {
        await this.page.goto('/');
        const menuButton = this.page
            .getByTestId('navigation-menu')
            .locator('[data-testid^="navigation-menu-"]')
            .nth(menuLevel);

        const tag = await menuButton.evaluate((el) => el.tagName);
        await menuButton.click();
        if (tag !== 'A') {
            await this.page.getByTestId('navigation-dropdown-captions').click();
        }

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
