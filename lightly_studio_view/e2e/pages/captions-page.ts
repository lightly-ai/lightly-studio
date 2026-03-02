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
     * If the button at `menuLevel` is the captions button itself (no siblings),
     * it clicks directly. Otherwise it hovers to open the dropdown and selects captions.
     *
     * @param menuLevel - Zero-based index of the menu button to interact with.
     */
    async goto(menuLevel: number = 1) {
        await this.page.goto('/');
        const menuButton = this.page
            .getByTestId('navigation-menu')
            .getByRole('link')
            .nth(menuLevel);

        // If this button IS the captions button, click it directly (no dropdown).
        // Otherwise, hover to open the dropdown and select captions from it.
        if ((await menuButton.getAttribute('data-testid')) === 'navigation-menu-captions') {
            await menuButton.click();
        } else {
            await menuButton.hover();
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

    async updateNthCaption(index: number, text: string) {
        await this.captionUtils.updateNthCaption(index, text);
    }
}
