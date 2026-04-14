import type { Locator, Page } from '@playwright/test';
import { expect } from '../utils';
import {
    VIDEO_SYNC_FIXTURE_COLORS,
    VIDEO_SYNC_FIXTURE_ROUTE
} from '../../src/lib/testing/videoSyncFixture';

export interface PlaybackDiagnostics {
    playerId: string;
    source: 'rvfc' | 'raf' | 'event';
    strategy: 'frame_start' | 'midpoint';
    currentTime: number;
    mediaTime: number | null;
    sourceTime: number;
    isPlaying: boolean;
    selectedFrameIndex: number | null;
    selectedFrameNumber: number | null;
    renderedFrameIndex: number | null;
    renderedFrameNumber: number | null;
    requestedFrameIndex: number | null;
    resolvedFrameIndex: number | null;
    pinnedFrameIndex: number | null;
}

export const gotoVideoSyncFixture = async (page: Page) => {
    await page.goto(VIDEO_SYNC_FIXTURE_ROUTE);
    await expect(page.getByTestId('video-sync-fixture-page')).toBeVisible();
};

export const getPlayerRoot = (page: Page, playerId: string): Locator =>
    page.locator(`[data-playback-player-id="${playerId}"]`);

export const getPlayerCanvas = (page: Page, playerId: string): Locator =>
    getPlayerRoot(page, playerId).getByTestId('canvas-video-player-canvas');

export const getPlayerDiagnostics = async (
    page: Page,
    playerId: string
): Promise<PlaybackDiagnostics> => {
    const text = await page.getByTestId(`video-playback-diagnostics-${playerId}`).textContent();
    if (!text?.trim()) {
        throw new Error(`Missing diagnostics for player ${playerId}`);
    }

    return JSON.parse(text) as PlaybackDiagnostics;
};

export const readCanvasCornerColor = async (
    page: Page,
    playerId: string
): Promise<[number, number, number]> => {
    return getPlayerCanvas(page, playerId).evaluate((canvas) => {
        const ctx = canvas.getContext('2d');
        if (!ctx) {
            throw new Error('Canvas context unavailable');
        }

        const data = ctx.getImageData(4, 4, 4, 4).data;
        let r = 0;
        let g = 0;
        let b = 0;
        let samples = 0;

        for (let index = 0; index < data.length; index += 4) {
            r += data[index];
            g += data[index + 1];
            b += data[index + 2];
            samples += 1;
        }

        return [Math.round(r / samples), Math.round(g / samples), Math.round(b / samples)] as [
            number,
            number,
            number
        ];
    });
};

export const decodeFixtureFrameIndex = (rgb: [number, number, number]): number => {
    let bestIndex = 0;
    let bestDistance = Number.POSITIVE_INFINITY;

    VIDEO_SYNC_FIXTURE_COLORS.forEach((color, index) => {
        const distance =
            (color[0] - rgb[0]) ** 2 + (color[1] - rgb[1]) ** 2 + (color[2] - rgb[2]) ** 2;
        if (distance < bestDistance) {
            bestDistance = distance;
            bestIndex = index;
        }
    });

    return bestIndex;
};

export const collectSyncSample = async (page: Page, playerId: string) => {
    const [rgb, diagnostics] = await Promise.all([
        readCanvasCornerColor(page, playerId),
        getPlayerDiagnostics(page, playerId)
    ]);

    return {
        rgb,
        videoFrameIndex: decodeFixtureFrameIndex(rgb),
        diagnostics
    };
};

export const expectPlayerToBeSynced = async (page: Page, playerId: string, timeoutMs = 3000) => {
    const deadline = Date.now() + timeoutMs;
    let lastSample: Awaited<ReturnType<typeof collectSyncSample>> | null = null;

    while (Date.now() < deadline) {
        try {
            lastSample = await collectSyncSample(page, playerId);
        } catch {
            await page.waitForTimeout(60);
            continue;
        }
        if (
            lastSample.diagnostics.renderedFrameIndex != null &&
            lastSample.videoFrameIndex === lastSample.diagnostics.renderedFrameIndex
        ) {
            return lastSample;
        }
        await page.waitForTimeout(60);
    }

    throw new Error(`Sync mismatch for ${playerId}: ${JSON.stringify(lastSample, null, 2)}`);
};

export const samplePlayingFrames = async (
    page: Page,
    playerId: string,
    targetDistinctFrames = 5
) => {
    const seen = new Set<number>();
    const samples: Array<Awaited<ReturnType<typeof collectSyncSample>>> = [];
    const deadline = Date.now() + 5000;

    while (Date.now() < deadline && seen.size < targetDistinctFrames) {
        const sample = await expectPlayerToBeSynced(page, playerId);
        samples.push(sample);
        seen.add(sample.videoFrameIndex);
        await page.waitForTimeout(120);
    }

    expect(seen.size).toBeGreaterThanOrEqual(Math.min(targetDistinctFrames, 3));
    return samples;
};

export const clickSliderAtFraction = async (page: Page, playerId: string, fraction: number) => {
    const slider = getPlayerRoot(page, playerId).getByTestId('canvas-video-player-slider');
    const box = await slider.boundingBox();
    if (!box) {
        throw new Error(`Missing slider bounding box for ${playerId}`);
    }

    await page.mouse.click(box.x + box.width * fraction, box.y + box.height / 2);
};

export const dragSlider = async (
    page: Page,
    playerId: string,
    startFraction: number,
    endFraction: number
) => {
    const slider = getPlayerRoot(page, playerId).getByTestId('canvas-video-player-slider');
    const box = await slider.boundingBox();
    if (!box) {
        throw new Error(`Missing slider bounding box for ${playerId}`);
    }

    await page.mouse.move(box.x + box.width * startFraction, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * endFraction, box.y + box.height / 2, {
        steps: 8
    });
    await page.mouse.up();
};
