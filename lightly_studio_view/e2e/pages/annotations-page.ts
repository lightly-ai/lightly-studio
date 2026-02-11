import { type Page, expect } from '@playwright/test';

export class AnnotationsPage {
    constructor(public readonly page: Page) {
        this.page = page;
    }

    async goto() {
        await this.page.goto('/');

        await expect(this.page.getByTestId('sample-grid-item').first()).toBeVisible({
            timeout: 10000
        });

        await this.page.getByTestId('navigation-menu-annotations').click();

        // Wait for the annotations grid to be visible
        await expect(this.getAnnotations().first()).toBeVisible({
            timeout: 10000
        });
    }

    getAnnotations() {
        return this.page.getByTestId('annotation-grid-item');
    }

    getSelectedItemsCount() {
        return this.page
            .locator('[data-testid="annotation-grid-item"] [data-state="checked"]')
            .count();
    }

    async clickLabel(label: string) {
        const responsePromise = this.page.waitForResponse(
            (response) => response.url().includes('/annotations') && response.status() === 200
        );

        await this.page
            .getByTestId('label-menu-label-name')
            .getByText(label, { exact: true })
            .click();

        await responsePromise;

        await this.getAnnotations().first().waitFor({
            state: 'attached',
            timeout: 10000
        });
    }

    async clickTag(tag: string) {
        await this.page.getByTestId('tag-menu-item').getByText(tag, { exact: true }).click();
    }

    async clickAnnotation(index: number) {
        // annotation-grid-item
        await this.getAnnotations().nth(index).dblclick();
    }

    async selectAnnotation(index: number) {
        // annotation-grid-item
        await this.getAnnotations().nth(index).click();
    }

    async selectLabelOption(label: string) {
        await this.page.getByRole('option', { name: label, exact: true }).click();
    }

    async startEditing() {
        await this.page.getByTestId('header-editing-mode-button').click();
        await expect(this.page.getByText('Finish Editing')).toBeVisible();
    }

    async setLabel(label: string) {
        // Wait for the PUT /annotations request to be completed after setting the label.
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'PUT' &&
                response.url().includes('/annotations') &&
                response.status() === 200
        );

        await this.page.getByTestId('select-list-trigger').click({ clickCount: 1 });
        const input = this.page.getByTestId('select-list-input');
        await input.waitFor({ state: 'visible' });
        await input.fill(label);
        // comment to trigger a fresh build
        await this.page.waitForLoadState('networkidle');
        await this.selectLabelOption(label);
        await responsePromise;
    }

    async selectAnnotationByIndex(index: number) {
        await this.getAnnotations().nth(index).getByRole('checkbox').click();
    }

    async selectTag(tag: string) {
        await this.page.getByText(tag, { exact: true }).click();
    }

    async createTag(tagName: string) {
        await this.page.getByTestId('tag-create-dialog-button').click();

        await this.page.getByTestId('tag-create-dialog-input').fill(tagName);

        await this.page.getByTestId('tag-create-dialog-create').click();

        await this.page.getByTestId('tag-create-dialog-save').click();
    }
}
