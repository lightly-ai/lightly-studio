import { type Page, expect } from '@playwright/test';
import { waitForRequestsToSettle } from '../utils';

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
        await expect(this.page.getByTestId('annotations-grid')).toBeVisible({
            timeout: 10000
        });

        // Wait for the annotations grid to be visible
        await expect(this.getAnnotations().first()).toBeVisible({
            timeout: 10000
        });
    }

    getAnnotations() {
        return this.page.getByTestId('annotation-grid-item');
    }

    getAnnotationByIndex(index: number) {
        return this.page.locator(`[data-annotation-index="${index}"]`);
    }

    getSelectedItemsCount() {
        return this.page
            .locator('[data-testid="annotation-grid-item"] [data-state="checked"]')
            .count();
    }

    async clickLabel(label: string) {
        const requestsSettled = waitForRequestsToSettle(this.page, '/annotations');

        await this.page
            .getByTestId('label-menu-label-name')
            .getByText(label, { exact: true })
            .click();

        await requestsSettled;
        await expect(this.page.getByTestId('annotations-grid')).toBeVisible({
            timeout: 10000
        });

        await expect(this.getAnnotations().first()).toBeVisible({
            timeout: 10000
        });
    }

    async clickTag(tag: string) {
        await this.page.getByTestId('tag-menu-item').getByText(tag, { exact: true }).click();
    }

    getTagsMenuItem(tagName: string) {
        return this.page.getByTestId('tags-menu-label').getByText(tagName, { exact: true });
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
        // Ensure all in-flight /annotations GET requests have settled before
        // triggering the PUT, to avoid DuckDB FK constraint violations from
        // concurrent sessions.
        await waitForRequestsToSettle(this.page, '/annotations');
        await this.selectLabelOption(label);
        await responsePromise;
    }

    async selectAnnotationByIndex(index: number) {
        await this.getAnnotations().nth(index).click();
    }

    async selectTag(tag: string) {
        await this.page.getByText(tag, { exact: true }).click();
    }

    async createTag(tagName: string) {
        const createTagResponsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.request().url().includes('/tags') &&
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
}
