import type { Request } from '@playwright/test';
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

    const waitForGroupedCounts = (tagCount: number) =>
        page.waitForResponse((response) => {
            if (!response.url().includes('/annotations/count-by-sample-tags')) return false;
            const body = response.request().postDataJSON() as { sample_tag_ids?: string[] };
            return response.status() === 200 && body.sample_tag_ids?.length === tagCount;
        });
    const selectTag = async (tagId: string, expectedCount: number) => {
        const option = page.getByTestId(`dataset-distribution-tag-option-${tagId}`);
        if (!(await option.isVisible())) {
            await page.getByTestId('dataset-distribution-tag-select').click();
        }
        const responsePromise = waitForGroupedCounts(expectedCount);
        await option.click();
        return responsePromise;
    };

    await selectTag(firstId!, 1);
    await selectTag(secondId!, 2);
    const response = await selectTag(emptyId!, 3);
    const requestBody = response.request().postDataJSON() as { sample_tag_ids: string[] };
    expect(requestBody.sample_tag_ids).toEqual([firstId, secondId, emptyId]);
    const groupedCounts = (await response.json()) as {
        sample_tag_id: string;
        counts: { count: number }[];
    }[];
    const emptyCounts = groupedCounts.find((item) => item.sample_tag_id === emptyId)?.counts;
    expect(emptyCounts?.length).toBeGreaterThan(0);
    expect(emptyCounts?.every((item) => item.count === 0)).toBe(true);

    await expect(page.getByText(/3 sample tags/)).toBeVisible();
    expect(page.url()).toBe(urlBeforeComparison);
    expect(navigationCount).toBe(0);
    expect(imageListRequestCount).toBe(0);
    page.off('framenavigated', recordNavigation);
    page.off('request', recordImageListRequest);
});
