import { test, expect } from '../utils';

test.describe('groups-menu-navigation', () => {
    test('navigate between collections', async ({ page }) => {
        await page.goto('/');

        // Verify groups page loads with group items
        await expect(page.getByTestId('group-grid-item').first()).not.toBeVisible();
        await expect(page.getByTestId('navigation-menu-photo')).toBeVisible();

        // Navigate to "photo" image collection via breadcrumb
        await page.getByTestId('navigation-menu-photo').click();
        await expect(page.getByTestId('sample-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-photo')).toBeVisible();

        // Navigate back to groups
        await page.getByTestId('navigation-menu-groups').click();
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-photo')).toBeVisible();

        // Navigate to "scan_upright" via dropdown (hover photo breadcrumb, click scan_upright)
        await page.getByTestId('navigation-menu-photo').hover();
        await page.getByTestId('navigation-dropdown-scan_upright').click();
        await expect(page.getByTestId('sample-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-scan_upright')).toBeVisible();

        // Navigate to "clips_video" via dropdown
        await page.getByTestId('navigation-menu-scan_upright').hover();
        await page.getByTestId('navigation-dropdown-clips_video').click();
        await expect(page.getByTestId('video-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-clips_video')).toBeVisible();

        // Navigate to video frames collection
        await page.getByTestId('navigation-menu-frames').click();
        await expect(page.getByTestId('frame-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-clips_video')).toBeVisible();

        // Navigate all the way back to groups
        await page.getByTestId('navigation-menu-groups').click();
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-photo')).toBeVisible();
    });
});
