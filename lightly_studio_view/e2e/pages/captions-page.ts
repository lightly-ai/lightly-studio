import { type Page, expect } from '@playwright/test';

export class CaptionsPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    async goto() {
        await this.page.goto('/');

        await expect(this.page.getByTestId('sample-grid-item').first()).toBeVisible({
            timeout: 10000
        });

        await this.page.getByTestId('navigation-menu-captions').click();

        // Wait for the captions grid to be visible
        await expect(this.getCaptions().first()).toBeVisible({
            timeout: 10000
        });
    }

    getCaptions() {
        return this.page.getByTestId('caption-grid-item');
    }
}
