import { expect, type Page } from '@playwright/test';
import { CaptionUtils } from '../caption-utils';
import { waitForRequestsToSettle } from '../utils';

export class SampleDetailsPage {
    private captionUtils: CaptionUtils;

    constructor(public readonly page: Page) {
        this.page = page;
        this.captionUtils = new CaptionUtils(page);
    }

    async pageIsReady() {
        await expect(this.getSampleDetails()).toBeVisible();
    }

    getSampleDetails() {
        return this.page.getByTestId('sample-details');
    }

    getLabelSelects() {
        return this.page.getByTestId('select-list-trigger');
    }

    getLabelInputs() {
        return this.page.getByTestId('select-list-input');
    }

    getSampleName() {
        return this.page.getByTestId('sample-metadata-filename');
    }

    getAnnotationBoxes() {
        return this.page.getByTestId('annotation_box');
    }

    getNextButton() {
        return this.page.getByRole('button', { name: 'Next sample' });
    }

    getPrevButton() {
        return this.page.getByRole('button', { name: 'Previous sample' });
    }

    async gotoNextAnnotation() {
        await this.getNextButton().click();
    }

    async gotoNextSampleByKeyboard() {
        await this.page.keyboard.press('ArrowRight');
    }

    async gotoPrevAnnotation() {
        await this.getPrevButton().click();
    }

    async gotoPrevAnnotationByKeyboard() {
        await this.page.keyboard.press('ArrowLeft');
    }

    async clickEditButton() {
        await this.page.getByTestId('header-editing-mode-button').click();
    }

    async hasAnnotationWithLabel(label: string) {
        return this.page.getByLabel(label).isVisible();
    }

    getAnnotationBoxByLabel(label: string) {
        return this.page.locator(`[data-testid="selectable-svg-group"] [data-label="${label}"]`);
    }

    async setLabel(label: string) {
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'PUT' &&
                response.url().includes('/annotations') &&
                response.status() === 200
        );

        await this.page.getByTestId('select-list-input').fill(label);
        await this.page.getByRole('option', { name: label, exact: true }).click();
        await this.pageIsReady();

        await responsePromise;
    }

    async setFirstAnnotationLabel(label: string) {
        await this.getLabelSelects().first().click();
        await this.setLabel(label);
    }

    getAddTagButton() {
        return this.page.getByRole('button', { name: 'Add tag' });
    }

    getAddTagInput() {
        return this.page.getByPlaceholder('Tag name…');
    }

    getTagByName(name: string) {
        return this.page.getByTestId('segment-tag-name').filter({ hasText: name });
    }

    getRemoveTagButton(tagName: string) {
        return this.page.getByTestId(`remove-tag-${tagName}`);
    }

    getCreateTagOption(tagName: string) {
        return this.page.getByText(tagName, { exact: true });
    }

    getExistingTagOption(tagName: string) {
        return this.page.getByRole('option', { name: tagName, exact: true });
    }

    async openAddTagPopover() {
        await this.getAddTagButton().click();
        await expect(this.getAddTagInput()).toBeVisible();
    }

    async addNewTag(tagName: string) {
        const createTagResponse = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                /\/tags(?:\?|$)/.test(response.request().url()) &&
                response.status() === 201
        );
        const addToSampleResponse = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/add/samples') &&
                response.status() >= 200 &&
                response.status() < 300
        );

        await this.openAddTagPopover();
        await this.getAddTagInput().fill(tagName);
        await this.getCreateTagOption(tagName).click();

        await createTagResponse;
        await addToSampleResponse;
        await waitForRequestsToSettle(this.page, '/tags');
        await expect(this.getTagByName(tagName)).toBeVisible();
    }

    async addExistingTag(tagName: string) {
        const addToSampleResponse = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/add/samples') &&
                response.status() >= 200 &&
                response.status() < 300
        );

        await this.openAddTagPopover();
        await this.getAddTagInput().fill(tagName);
        await this.getExistingTagOption(tagName).click();

        await addToSampleResponse;
        await waitForRequestsToSettle(this.page, '/tags');
        await expect(this.getTagByName(tagName)).toBeVisible();
    }

    async removeTag(tagName: string) {
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'DELETE' &&
                response.url().includes('/tag/') &&
                response.status() === 200
        );

        await this.getRemoveTagButton(tagName).click();

        await responsePromise;
        await expect(this.getTagByName(tagName)).toHaveCount(0);
    }

    // Captions

    getCaptionCount() {
        return this.captionUtils.getCaptionCount();
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

    async addCaption() {
        await this.captionUtils.addCaption();
    }

    async deleteNthCaption(index: number) {
        await this.captionUtils.deleteNthCaption(index);
    }

    async undoLastCaptionDelete() {
        await this.captionUtils.undoLastCaptionDelete();
    }

    async updateNthCaption(index: number, text: string) {
        await this.captionUtils.updateNthCaption(index, text);
    }
}
