import { test, expect } from '../../utils';

test.describe('sample-details-tag-flow', () => {
    test('user can create and attach multiple new tags in sample details', async ({
        samplesPage,
        sampleDetailsPage
    }) => {
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        const firstTagName = `e2e-tag-${Date.now()}-1`;
        const secondTagName = `e2e-tag-${Date.now()}-2`;

        await expect(sampleDetailsPage.getTagByName(firstTagName)).toHaveCount(0);
        await expect(sampleDetailsPage.getTagByName(secondTagName)).toHaveCount(0);

        await sampleDetailsPage.addNewTag(firstTagName);
        await sampleDetailsPage.addNewTag(secondTagName);

        await expect(sampleDetailsPage.getTagByName(firstTagName)).toHaveText(firstTagName);
        await expect(sampleDetailsPage.getTagByName(secondTagName)).toHaveText(secondTagName);
        await expect(sampleDetailsPage.page.getByTestId('segment-tag-name')).toContainText([
            firstTagName,
            secondTagName
        ]);
    });
});
