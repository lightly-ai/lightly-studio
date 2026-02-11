import { expect, type Page } from '@playwright/test';
import { CaptionUtils } from '../caption-utils';

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

    async createSegmentationAnnotation() {
        const responsePromise = this.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/annotations') &&
                response.status() === 201
        );

        await this.page.getByRole('button', { name: 'Segmentation Mask Brush' }).click();

        const interactionRect = this.page
            .locator('rect[role="button"][style*="crosshair"]')
            .first();
        await expect(interactionRect).toBeVisible();

        const box = await interactionRect.boundingBox();
        if (!box) {
            throw new Error('Interaction rectangle bounding box is not available');
        }

        const startX = box.x + box.width * 0.3;
        const startY = box.y + box.height * 0.3;
        const endX = box.x + box.width * 0.35;
        const endY = box.y + box.height * 0.35;

        await this.page.mouse.move(startX, startY);
        await this.page.mouse.down();
        await this.page.mouse.move(endX, endY);
        await this.page.mouse.up();

        await responsePromise;
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

    async updateNthCaption(index: number, text: string) {
        await this.captionUtils.updateNthCaption(index, text);
    }
}
