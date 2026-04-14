import { expect, type Page } from '@playwright/test';
import { waitForRequestsToSettle } from '../utils';

export class VideoFramesPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    async goto() {
        await this.page.goto('/');
        await this.page.getByTestId('navigation-menu-frames').click();
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
        return this.page.locator(`[data-index="${index}"]`);
    }

    getTagsMenuItem(tagName: string) {
        return this.page.getByTestId('tags-menu-label').getByText(tagName, { exact: true });
    }

    async getNumSelectedSamples(): Promise<number> {
        const boxes = await this.page.getByTestId('sample-selected-box');
        const count = await boxes.count();
        let selectedCount = 0;
        for (let i = 0; i < count; i++) {
            const isChecked = await boxes.nth(i).isChecked();
            if (isChecked) {
                selectedCount++;
            }
        }
        return selectedCount;
    }

    async createTag(tagName: string): Promise<void> {
        const createTagResponsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                /\/tags(?:\?|$)/.test(response.request().url()) &&
                response.status() === 201
        );
        const assignTagResponsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/add/samples') &&
                response.status() >= 200 &&
                response.status() < 300
        );

        const tagInput = this.page.getByPlaceholder('Assign tag to selection');
        await expect(tagInput).toBeEnabled();
        await tagInput.fill(tagName);
        await this.page.getByRole('button', { name: `Create "${tagName}"` }).click();

        await createTagResponsePromise;
        await assignTagResponsePromise;
        await waitForRequestsToSettle(this.page, '/tags');
        await expect(this.getTagsMenuItem(tagName)).toBeVisible();
    }

    async pressTag(tagName: string): Promise<void> {
        await expect(this.getVideoFrames().first()).toBeVisible();

        const responsePromise = this.page.waitForResponse(
            (response) => response.url().includes('/frame') && response.status() === 200
        );

        const tagLabels = this.page.getByTestId('tags-menu-label');
        const labelCount = await tagLabels.count();
        for (let i = 0; i < labelCount; i++) {
            const labelText = await tagLabels.nth(i).textContent();
            if (labelText === tagName) {
                await tagLabels.nth(i).click();
                break;
            }
        }

        await responsePromise;
        await this.getVideoFrames().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
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
