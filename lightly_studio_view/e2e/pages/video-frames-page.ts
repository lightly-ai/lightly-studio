import { expect, type Page } from '@playwright/test';

export class VideoFramesPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    async goto() {
        await this.page.goto('/');
        await this.page.getByTestId('navigation-menu-frames').click();

        // Wait for frame grid items to be visible
        await expect(this.getVideoFrames().first()).toBeVisible({
            timeout: 10000
        });
    }

    getVideoFrames() {
        return this.page.getByTestId('frame-grid-item');
    }

    getLabelsMenuItem(labelName: string) {
        return this.page.getByTestId('label-menu-label-name').getByText(labelName, { exact: true });
    }

    async clickLabel(label: string) {
        const responsePromise = this.page.waitForResponse(
            (response) => response.url().includes('/frame') && response.status() === 200
        );

        const labelMenuItem = this.getLabelsMenuItem(label);
        await labelMenuItem.click();

        await responsePromise;
        // TODO(Horatiu 01/2026): 10s timeout might be too long, investigate if we can reduce it everywhere
        await this.getVideoFrames().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
    }
}
