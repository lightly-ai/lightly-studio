import { expect, type Page } from '@playwright/test';

export class VideosPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    async goto() {
        await this.page.goto('/');
        await this.page.getByTestId('navigation-menu-videos').click();

        // Wait for video grid items to be visible
        await expect(this.getVideos().first()).toBeVisible({
            timeout: 10000
        });
    }

    getVideos() {
        return this.page.getByTestId('video-grid-item');
    }
}
