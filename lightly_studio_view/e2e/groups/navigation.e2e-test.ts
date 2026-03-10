import { test, expect } from '../utils';

test.describe('groups-menu-navigation', () => {
    test('navigate between collections', async ({ page }) => {
        await page.goto('/');

        // 1. Verify groups page loads with group items
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();

        // 2. Navigate to "photo" image collection via breadcrumb
        await page.getByTestId('navigation-menu-photo').click();
        await expect(page.getByTestId('sample-grid-item').first()).toBeVisible();

        // 3. Navigate back to groups
        await page.getByTestId('navigation-menu-groups').click();
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();

        // 4. Navigate to "scan_upright" via dropdown (hover photo breadcrumb, click scan_upright)
        await page.getByTestId('navigation-menu-photo').hover();
        await page.getByTestId('navigation-dropdown-scan_upright').click();
        await expect(page.getByTestId('sample-grid-item').first()).toBeVisible();

        // 5. Navigate back to groups
        await page.getByTestId('navigation-menu-groups').click();
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();

        // 6. Navigate to "clips_video" via dropdown
        await page.getByTestId('navigation-menu-photo').hover();
        await page.getByTestId('navigation-dropdown-clips_video').click();
        await expect(page.getByTestId('video-grid-item').first()).toBeVisible();

        // 7. Navigate to video frames collection
        await page.getByTestId('navigation-menu-frames').click();
        await expect(page.getByTestId('frame-grid-item').first()).toBeVisible();

        // 8. Navigate all the way back to groups
        await page.getByTestId('navigation-menu-groups').click();
        await expect(page.getByTestId('group-grid-item').first()).toBeVisible();
    });
});
