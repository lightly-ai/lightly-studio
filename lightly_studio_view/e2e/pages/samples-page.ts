import { expect, type Page } from '@playwright/test';
import { pressButton } from '../utils';

export class SamplesPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    async goto() {
        await this.page.goto('/');
        await this.page.getByTestId('navigation-menu-images').click();

        // Wait for sample grid items to be visible
        await expect(this.getSamples().first()).toBeVisible({
            timeout: 10000
        });
    }

    getSamples() {
        return this.page.getByTestId('sample-grid-item');
    }

    async startEditing() {
        await this.page.getByTestId('header-editing-mode-button').click();
        await expect(this.page.getByText('Done')).toBeVisible();
    }

    async doubleClickFirstSample() {
        await this.doubleClickNthSample(0);
    }

    getSampleByIndex(index: number) {
        return this.getSamples().nth(index);
    }

    getSampleByName(name: string) {
        return this.page.locator(`[data-sample-name="${name}"]`);
    }

    getAnnotationByLabel(sample: string, label: string) {
        return this.page.locator(
            `[data-sample-name="${sample}"] [data-annotation-label="${label}"] [data-testid="annotation_box"]`
        );
    }

    async getAnnotationsByLabel(sample: string, label: string) {
        return await this.page
            .locator(
                `[data-sample-name="${sample}"] [data-annotation-label="${label}"] [data-testid="annotation_box"]`
            )
            .all();
    }

    getLabelsMenuItem(labelName: string) {
        return this.page.getByTestId('label-menu-label-name').getByText(labelName, { exact: true });
    }

    getTagsMenuItem(tagName: string) {
        return this.page.getByTestId('tags-menu-label').getByText(tagName, { exact: true });
    }

    async clickLabel(label: string) {
        const responsePromise = this.page.waitForResponse(
            (response) => response.url().includes('/images/list') && response.status() === 200
        );

        const labelMenuItem = this.getLabelsMenuItem(label);
        await labelMenuItem.click();

        await responsePromise;

        await this.getSamples().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
    }

    /**
     * Performs an embedding-based text search and waits for results to load.
     *
     * @param searchTerm - The text to search for (pass empty string to clear the search)
     * @returns Promise that resolves when the API call completes
     *
     * @example
     * await samplesPage.textSearch('bear');
     * // Now samples are filtered by text search
     *
     * @example
     * await samplesPage.textSearch('');
     * // Clears the search and reloads all samples
     */
    async textSearch(searchTerm: string): Promise<void> {
        const clearButton = this.page.getByTestId('search-clear-button');

        if (await clearButton.isVisible()) {
            const clearResponsePromise = this.page.waitForResponse(
                (response) => response.url().includes('/images/list') && response.status() === 200
            );
            await clearButton.click();
            await clearResponsePromise;
        }

        if (searchTerm.trim() === '') {
            await this.getSamples().first().waitFor({ state: 'attached', timeout: 10000 });
            return;
        }

        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.url().includes(`query_text=${searchTerm}`) && response.status() === 200
        );

        const searchInput = this.page.getByTestId('text-embedding-search-input');
        await expect(searchInput).toBeVisible();
        await searchInput.fill(searchTerm);
        await this.page.keyboard.press('Enter');

        await responsePromise;

        await this.getSamples().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
    }

    async createSelection(
        strategy: 'diversity' | 'typicality',
        nSamples: number,
        tagName: string
    ): Promise<void> {
        await this.page.getByTestId('menu-trigger').click();
        await this.page.getByTestId('menu-selection').click();

        await this.page.getByTestId('selection-dialog-strategy-select').click();
        await this.page.getByTestId(`selection-strategy-${strategy}`).click();

        const nSamplesInput = this.page.getByTestId('selection-dialog-n-samples-input');
        await nSamplesInput.clear();
        await nSamplesInput.fill(nSamples.toString());

        const tagNameInput = this.page.getByTestId('selection-dialog-tag-name-input');
        await tagNameInput.fill(tagName);

        await pressButton(this.page, 'selection-dialog-submit');
    }

    async createDiversitySelection(nSamples: number, tagName: string): Promise<void> {
        return this.createSelection('diversity', nSamples, tagName);
    }

    async createTypicalitySelection(nSamples: number, tagName: string): Promise<void> {
        return this.createSelection('typicality', nSamples, tagName);
    }

    async pressTag(tagName: string): Promise<void> {
        await expect(this.page.getByTestId('sample-grid-item').first()).toBeVisible();

        const tagLabels = this.page.getByTestId('tags-menu-label');
        const labelCount = await tagLabels.count();
        for (let i = 0; i < labelCount; i++) {
            const labelText = await tagLabels.nth(i).textContent();
            if (labelText === tagName) {
                await tagLabels.nth(i).click();
                break;
            }
        }

        await this.getSamples().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
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

    async getTagNames(): Promise<string[]> {
        const tagLabels = this.page.getByTestId('tags-menu-label');
        const tagLabelsText: string[] = [];
        const labelCount = await tagLabels.count();
        for (let i = 0; i < labelCount; i++) {
            const labelText = await tagLabels.nth(i).textContent();
            if (labelText) tagLabelsText.push(labelText);
        }
        return tagLabelsText;
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

    async doubleClickNthSample(index: number): Promise<void> {
        await this.getSampleByIndex(index).dblclick();
        await this.page.getByTestId('sample-details-loading').waitFor({ state: 'hidden' });
    }
}
