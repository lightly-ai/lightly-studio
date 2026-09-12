import { expect, test } from '../utils';

// Chromium starts a native <img> drag once the pointer moves a few pixels between mousedown
// and mouseup, and a started drag swallows the click. Frame thumbnails are <img> elements.
const CLICK_DRIFT_PX = 6;

test('a click that drifts a few pixels still toggles frame selection', async ({
    page,
    videoFramesPage
}) => {
    const frame = videoFramesPage.getVideoFrameByIndex(1);
    await expect(frame).toBeVisible();
    const box = await frame.boundingBox();
    expect(box).not.toBeNull();

    const x = box!.x + box!.width / 2;
    const y = box!.y + box!.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + CLICK_DRIFT_PX, y + 2, { steps: 3 });
    await page.mouse.up();

    expect(await videoFramesPage.getNumSelectedSamples()).toBe(1);
});
