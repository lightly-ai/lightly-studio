import type { Request } from '@playwright/test';
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

    test('already attached tags cannot be added again', async ({
        samplesPage,
        sampleDetailsPage
    }) => {
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        const tagName = `e2e-tag-${Date.now()}-duplicate`;

        await sampleDetailsPage.addNewTag(tagName);
        await expect(sampleDetailsPage.getTagByName(tagName)).toHaveCount(1);

        await sampleDetailsPage.openAddTagPopover();
        await sampleDetailsPage.getAddTagInput().fill(tagName);

        await expect(sampleDetailsPage.getExistingTagOption(tagName)).toHaveCount(0);
        await expect(sampleDetailsPage.page.getByText('No tags found')).toBeVisible();
        await expect(sampleDetailsPage.getTagByName(tagName)).toHaveCount(1);
    });

    test('user can delete a tag created in sample details', async ({
        samplesPage,
        sampleDetailsPage
    }) => {
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        const tagName = `e2e-tag-${Date.now()}-remove`;

        await sampleDetailsPage.addNewTag(tagName);
        await sampleDetailsPage.removeTag(tagName);
    });

    test('existing tags can be added after navigating to the next sample', async ({
        samplesPage,
        sampleDetailsPage
    }) => {
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        const firstSampleName = await sampleDetailsPage.getSampleName().textContent();
        const tagName = `e2e-tag-${Date.now()}-reuse`;

        await sampleDetailsPage.addNewTag(tagName);

        const createTagRequests: string[] = [];
        const trackCreateTagRequests = (request: Request) => {
            if (request.method() === 'POST' && request.url().includes('/tags')) {
                createTagRequests.push(request.url());
            }
        };

        sampleDetailsPage.page.on('request', trackCreateTagRequests);
        try {
            await sampleDetailsPage.gotoNextSampleByKeyboard();
            await expect(sampleDetailsPage.getSampleName()).not.toHaveText(firstSampleName!);

            await sampleDetailsPage.addExistingTag(tagName);
            await expect(sampleDetailsPage.getTagByName(tagName)).toHaveCount(1);
        } finally {
            sampleDetailsPage.page.off('request', trackCreateTagRequests);
        }

        expect(createTagRequests).toHaveLength(0);
    });
});
