import { expect, type Page } from '@playwright/test';
import { pressButton } from '../utils';

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

    getVideoByIndex(index: number) {
        return this.getVideos().nth(index);
    }

    getVideoByName(name: string) {
        return this.page.locator(`[data-sample-name="${name}"]`);
    }

    getLabelsMenuItem(labelName: string) {
        return this.page.getByTestId('label-menu-label-name').getByText(labelName, { exact: true });
    }

    async clickLabel(label: string) {
        const responsePromise = this.page.waitForResponse(
            (response) => response.url().includes('/video') && response.status() === 200
        );

        const labelMenuItem = this.getLabelsMenuItem(label);
        await labelMenuItem.click();

        await responsePromise;

        await this.getVideos().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
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
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/tags') &&
                response.status() === 201
        );

        await pressButton(this.page, 'tag-create-dialog-button');
        const tagTextInput = this.page.getByTestId('tag-create-dialog-input');
        await tagTextInput.click();

        await this.page.waitForTimeout(10);
        await this.page.keyboard.type(tagName);
        await this.page.waitForTimeout(100);
        await pressButton(this.page, 'tag-create-dialog-create');
        await pressButton(this.page, 'tag-create-dialog-save');

        await responsePromise;
    }

    getTagsMenuItem(tagName: string) {
        return this.page.getByTestId('tags-menu-label').getByText(tagName, { exact: true });
    }

    async pressTag(tagName: string): Promise<void> {
        await expect(this.getVideos().first()).toBeVisible();

        const responsePromise = this.page.waitForResponse(
            (response) => response.url().includes('/video') && response.status() === 200
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

        await this.getVideos().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
    }
}
