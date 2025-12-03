import { test, expect } from '../utils';
import { cocoDataset } from './fixtures';

test.beforeEach(async ({ annotationsPage }) => {
    await annotationsPage.goto();
});

test('user can change label of an annotation grid page', async ({ annotationsPage }) => {
    await annotationsPage.startEditing();

    // Check initial apple annotation count
    await annotationsPage.clickLabel(cocoDataset.labels.apple.name);
    await expect(annotationsPage.getAnnotations()).toHaveCount(
        cocoDataset.labels.apple.annotationCount
    );
    await annotationsPage.clickLabel(cocoDataset.labels.apple.name);

    // Check initial airplane annotation count
    await annotationsPage.clickLabel(cocoDataset.labels.airplane.name);
    await expect(annotationsPage.getAnnotations()).toHaveCount(
        cocoDataset.labels.airplane.annotationCount
    );

    // Mark 2 annotations as apples
    await expect(await annotationsPage.getSelectedItemsCount()).toBe(0);
    await annotationsPage.selectAnnotation(0);
    await annotationsPage.selectAnnotation(1);
    await expect(await annotationsPage.getSelectedItemsCount()).toBe(2);
    await annotationsPage.setLabel(cocoDataset.labels.apple.name);

    // Check airplane count after moving 2 to apple
    await expect(annotationsPage.getAnnotations()).toHaveCount(
        cocoDataset.labels.airplane.annotationCount - 2,
        {
            timeout: 10000
        }
    );

    // Unselect airplane and select apple
    await annotationsPage.clickLabel(cocoDataset.labels.airplane.name);
    await annotationsPage.clickLabel(cocoDataset.labels.apple.name);

    // Ensure no annotations are selected after the update, check apple count after receiving 2 from airplane
    await expect(await annotationsPage.getSelectedItemsCount()).toBe(0);
    await expect(annotationsPage.getAnnotations()).toHaveCount(
        cocoDataset.labels.apple.annotationCount + 2
    );

    // Mark last 2 annotations back as airplane
    await annotationsPage.selectAnnotation(2);
    await annotationsPage.selectAnnotation(3);
    await annotationsPage.setLabel(cocoDataset.labels.airplane.name);
    await expect(annotationsPage.getAnnotations()).toHaveCount(
        cocoDataset.labels.apple.annotationCount
    );

    // Check airplane count after restoration (should be back to original)
    await annotationsPage.clickLabel(cocoDataset.labels.apple.name);
    await annotationsPage.clickLabel(cocoDataset.labels.airplane.name);
    await expect(annotationsPage.getAnnotations()).toHaveCount(
        cocoDataset.labels.airplane.annotationCount
    );
});
