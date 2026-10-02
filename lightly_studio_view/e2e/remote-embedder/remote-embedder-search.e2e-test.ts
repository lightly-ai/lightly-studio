import type { APIRequestContext, Page } from '@playwright/test';
import { expect, test } from '../utils';

// The server that `lightly_studio/e2e-tests/remote_embedder_server.py` runs.
const EMBED_COUNT_URL = 'http://127.0.0.1:8011/test/embed-count';
const API_KEY = 'e2e-remote-embedder-key';

test('text search embeds the query on the remote server', async ({ samplesPage, request }) => {
    const countBefore = await getEmbedCount(request);

    await samplesPage.textSearch('red');

    await expect(samplesPage.getSampleByIndex(0)).toHaveAttribute('data-sample-name', 'red.png');
    expect(await getEmbedCount(request)).toBe(countBefore + 1);
});

test('pasted-image search embeds the image on the remote server', async ({
    page,
    samplesPage,
    request
}) => {
    const countBefore = await getEmbedCount(request);

    const listResponse = page.waitForResponse(
        (response) =>
            response.url().includes('/images/list') &&
            response.request().postData()?.includes('text_embedding') === true
    );
    await pasteImage(page, await solidPngDataUrl(page, '#00ff00'));
    await listResponse;

    await expect(samplesPage.getSampleByIndex(0)).toHaveAttribute('data-sample-name', 'green.png');
    // Without the server, the backend falls back to the local image embedder.
    expect(await getEmbedCount(request)).toBe(countBefore + 1);
});

async function getEmbedCount(request: APIRequestContext): Promise<number> {
    const response = await request.get(EMBED_COUNT_URL, {
        headers: { Authorization: `Bearer ${API_KEY}` }
    });
    expect(response.ok()).toBe(true);
    return (await response.json()).count;
}

async function solidPngDataUrl(page: Page, color: string): Promise<string> {
    return page.evaluate((fillColor) => {
        const canvas = document.createElement('canvas');
        canvas.width = 8;
        canvas.height = 8;
        const context = canvas.getContext('2d');
        if (!context) {
            throw new Error('The canvas has no 2d context.');
        }
        context.fillStyle = fillColor;
        context.fillRect(0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/png');
    }, color);
}

async function pasteImage(page: Page, dataUrl: string): Promise<void> {
    await page.getByTestId('text-embedding-search-input').evaluate(async (input, url) => {
        const blob = await (await fetch(url)).blob();
        const clipboardData = new DataTransfer();
        clipboardData.items.add(new File([blob], 'pasted.png', { type: 'image/png' }));
        input.dispatchEvent(
            new ClipboardEvent('paste', { clipboardData, bubbles: true, cancelable: true })
        );
    }, dataUrl);
}
