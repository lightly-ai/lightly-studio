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

    getVideoFrameByIndex(index: number) {
        return this.getVideoFrames().nth(index);
    }

    async doubleClickFirstVideoFrame() {
        await this.doubleClickNthVideoFrame(0);
    }

    async doubleClickNthVideoFrame(index: number): Promise<void> {
        await this.getVideoFrameByIndex(index).dblclick();
        await this.page.getByTestId('sample-details-loading').waitFor({ state: 'hidden' });
    }

    async pageIsReady() {
        await expect(this.getSampleDetails()).toBeVisible();
    }

    getSampleDetails() {
        return this.page.getByTestId('video-frame-details');
    }
}
