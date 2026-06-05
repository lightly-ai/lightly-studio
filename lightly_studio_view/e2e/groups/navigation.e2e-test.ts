import { test, expect } from '../utils';

test.describe('groups-menu-navigation', () => {
    test('navigate between collections', async ({ page }) => {
        await page.goto('/');

        // Verify groups page loads with group items
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-photo')).toBeVisible();

        // Navigate to "photo" image collection via breadcrumb dropdown
        await page.getByTestId('navigation-menu-photo').click();
        await page.getByTestId('navigation-dropdown-photo').click();
        await expect(page.getByTestId('sample-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-photo')).toBeVisible();

        // Navigate back to groups (root level renders as a link)
        await page.getByTestId('navigation-menu-groups').click();
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-photo')).toBeVisible();

        // Navigate to "scan_upright" via photo breadcrumb dropdown
        await page.getByTestId('navigation-menu-photo').click();
        await page.getByTestId('navigation-dropdown-scan_upright').click();
        await expect(page.getByTestId('sample-grid-item').first()).toBeVisible();
        await expect(page.getByTestId('navigation-menu-scan_upright')).toBeVisible();

        // Navigate to "clips_video" via scan_upright breadcrumb dropdown
        await page.getByTestId('navigation-menu-scan_upright').click();
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
