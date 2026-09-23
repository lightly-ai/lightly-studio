import type { Request, Response } from '@playwright/test';
import { expect, test } from '../utils';
import { distributionComparison } from './fixtures';

test('compares overlapping and empty sample tags without reloading or filtering the grid', async ({
    page,
    samplesPage
}) => {
    const firstId = await samplesPage.getTagIdByName(distributionComparison.firstTag);
    const secondId = await samplesPage.getTagIdByName(distributionComparison.secondTag);
    const emptyId = await samplesPage.getTagIdByName(distributionComparison.emptyTag);
    expect(firstId).toBeTruthy();
    expect(secondId).toBeTruthy();
    expect(emptyId).toBeTruthy();

    await page.getByTestId('side-panel-tabs-distribution').click();
    await expect(page.getByTestId('dataset-distribution-panel')).toBeVisible();

    const urlBeforeComparison = page.url();
    let navigationCount = 0;
    let imageListRequestCount = 0;
    const recordNavigation = () => navigationCount++;
    const recordImageListRequest = (request: Request) => {
        if (request.url().includes('/images/list')) imageListRequestCount++;
    };
    page.on('framenavigated', recordNavigation);
    page.on('request', recordImageListRequest);

    // Waits for the grouped-counts response that carries exactly `tagCount` tag IDs.
    const waitForGroupedCounts = (tagCount: number): Promise<Response> =>
        page.waitForResponse((response) => {
            if (!response.url().includes('/annotations/count-by-sample-tags')) return false;
            const body = response.request().postDataJSON() as { sample_tag_ids?: string[] };
            return response.status() === 200 && body.sample_tag_ids?.length === tagCount;
        });

    // Opens the tag selector if needed, clicks the tag option, and waits for
    // the API response carrying the updated selection.
    const selectTag = async (tagId: string, expectedTagCount: number): Promise<Response> => {
        const option = page.getByTestId(`dataset-distribution-tag-option-${tagId}`);
        if (!(await option.isVisible())) {
            await page.getByTestId('dataset-distribution-tag-select').click();
        }
        const responsePromise = waitForGroupedCounts(expectedTagCount);
        await option.click();
        return responsePromise;
    };

    await selectTag(firstId!, 1);
    await selectTag(secondId!, 2);
    const response = await selectTag(emptyId!, 3);

    // Verify the final request carries all three tag IDs in selection order.
    const requestBody = response.request().postDataJSON() as { sample_tag_ids: string[] };
    expect(requestBody.sample_tag_ids).toEqual([firstId, secondId, emptyId]);

    // The empty tag must appear in the response with every class at count 0.
    const groupedCounts = (await response.json()) as {
        sample_tag_id: string;
        counts: { count: number }[];
    }[];
    const emptyCounts = groupedCounts.find((g) => g.sample_tag_id === emptyId)?.counts;
    expect(emptyCounts?.length).toBeGreaterThan(0);
    expect(emptyCounts?.every((c) => c.count === 0)).toBe(true);

    // Selecting comparison tags must not navigate or re-fetch the image grid.
    await expect(page.getByText(/3 sample tags/)).toBeVisible();
    expect(page.url()).toBe(urlBeforeComparison);
    expect(navigationCount).toBe(0);
    expect(imageListRequestCount).toBe(0);

    page.off('framenavigated', recordNavigation);
    page.off('request', recordImageListRequest);
});
