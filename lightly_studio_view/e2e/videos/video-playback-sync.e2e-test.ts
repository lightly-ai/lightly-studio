import { test, expect } from '../utils';
import {
    clickSliderAtFraction,
    collectSyncSample,
    dragSlider,
    expectPlayerToBeSynced,
    getPlayerRoot,
    gotoVideoSyncFixture,
    samplePlayingFrames
} from './video-playback-sync.helpers';

test.describe('video-playback-sync', () => {
    test('detail active playback stays synced on the synthetic fixture', async ({ page }) => {
        await gotoVideoSyncFixture(page);

        const detailPlayer = getPlayerRoot(page, 'detail-player');
        await detailPlayer.getByRole('button', { name: 'Play video' }).click();

        const samples = await samplePlayingFrames(page, 'detail-player', 5);
        expect(samples.every((sample) => sample.diagnostics.isPlaying)).toBe(true);
    });

    test('detail paused timeline clicks and drag land on the correct frame', async ({ page }) => {
        await gotoVideoSyncFixture(page);

        await clickSliderAtFraction(page, 'detail-player', 0.2);
        let sample = await expectPlayerToBeSynced(page, 'detail-player');
        expect(sample.diagnostics.isPlaying).toBe(false);

        await clickSliderAtFraction(page, 'detail-player', 0.55);
        sample = await expectPlayerToBeSynced(page, 'detail-player');
        expect(sample.diagnostics.isPlaying).toBe(false);

        await dragSlider(page, 'detail-player', 0.1, 0.8);
        sample = await expectPlayerToBeSynced(page, 'detail-player');
        expect(sample.diagnostics.isPlaying).toBe(false);
    });

    test('grid hover autoplay preview stays synced while playing', async ({ page }) => {
        await gotoVideoSyncFixture(page);

        await page.getByTestId('video-sync-preview-trigger').hover();
        await expect(getPlayerRoot(page, 'preview-player')).toBeVisible();

        const samples = await samplePlayingFrames(page, 'preview-player', 4);
        expect(samples.some((sample) => sample.diagnostics.source === 'rvfc')).toBe(true);

        const finalSample = await collectSyncSample(page, 'preview-player');
        expect(finalSample.videoFrameIndex).toBe(finalSample.diagnostics.renderedFrameIndex);
    });
});
