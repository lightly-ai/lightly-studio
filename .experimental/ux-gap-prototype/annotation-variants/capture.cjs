// Captures the same task in each column: "add a deer box to model_v2 on sample 1 of 5000".
// Run from lightly_studio_view so Playwright resolves:
//   NODE_PATH=node_modules node ../.experimental/ux-gap-prototype/annotation-variants/capture.cjs
// Needs main on 8015, the pencil variant on 8016 and the radio variant on 8014, each on its own
// copy of demo.db (see README.md).
const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, 'shots');
const SAMPLE_PATH =
    '/datasets/3d6764c7-546f-4755-bc93-e0ed6da72bc5/image/3d6764c7-546f-4755-bc93-e0ed6da72bc5' +
    '/images/54c57397-fd20-4004-98f9-e0e8aafd3919';

const COLUMNS = [
    {
        name: 'main',
        url: `http://localhost:8015${SAMPLE_PATH}`,
        pick: async (page) => {
            await page.getByTestId('annotation-source-pill-trigger').click();
            await page.getByTestId('annotation-source-pill-option-model_v2').click();
        }
    },
    {
        name: 'pencil',
        url: `http://localhost:8016${SAMPLE_PATH}?annotateVariant=pencil`,
        drawBeforePick: true,
        pick: (page) => page.getByTestId('annotation-target-model_v2').click()
    },
    {
        name: 'radio',
        url: `http://localhost:8014${SAMPLE_PATH}?annotateVariant=radio`,
        drawBeforePick: true,
        pick: (page) => page.getByTestId('annotation-target-radio-model_v2').click()
    }
];

const pause = (page, ms = 900) => page.waitForTimeout(ms);

async function drawBox(page) {
    await page.getByRole('button', { name: 'Bounding Box Tool' }).click();
    const canvas = await page.locator('foreignObject img').first();
    const box = await canvas.boundingBox();
    const x0 = box.x + box.width * 0.55;
    const y0 = box.y + box.height * 0.3;
    await page.mouse.move(x0, y0);
    await page.mouse.down();
    await page.mouse.move(x0 + box.width * 0.15, y0 + box.height * 0.15, { steps: 12 });
    await page.mouse.up();
    await pause(page, 600);
}

async function chooseDeerIfAsked(page) {
    const classInput = page.getByPlaceholder(/class/i).first();
    if (await classInput.isVisible().catch(() => false)) {
        await classInput.fill('deer');
        await pause(page, 400);
        await page.keyboard.press('Enter');
    }
}

async function capture(browser, column) {
    // 2x, so text stays sharp when Slack scales the images.
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2
    });
    const page = await context.newPage();
    const shot = (step) =>
        page.screenshot({ path: path.join(OUT, `${column.name}-${step}.png`) });

    await page.goto(column.url);
    await page.getByRole('button', { name: /^Edit/ }).click();
    await pause(page, 1500);
    await shot('1-edit-mode');

    if (column.drawBeforePick) {
        await drawBox(page);
        await pause(page, 300);
        await shot('2-draw-before-pick');
        await page.getByRole('button', { name: 'Selection' }).click();
    }

    await column.pick(page);
    await pause(page);
    await shot('3-picked-model_v2');

    await drawBox(page);
    await chooseDeerIfAsked(page);
    await pause(page, 1500);
    await shot('4-deer-box-in-model_v2');

    const addClassification = page.getByTestId('add-classification-button');
    if (await addClassification.isVisible().catch(() => false)) {
        await addClassification.scrollIntoViewIfNeeded();
        await pause(page, 500);
        await shot('5-classification');
    }

    await context.close();
}

(async () => {
    fs.mkdirSync(OUT, { recursive: true });
    // Uses the cached headless shell, so no browser download is needed.
    const browser = await chromium.launch({
        executablePath:
            process.env.CHROMIUM ??
            `${process.env.HOME}/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell`
    });
    const only = process.argv[2];
    for (const column of COLUMNS.filter((c) => !only || c.name === only)) {
        console.log(`capturing ${column.name}`);
        await capture(browser, column);
    }
    await browser.close();
})();
