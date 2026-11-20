import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SceneViewSettings from './SceneViewSettings.svelte';

const defaultProps = {
    orthographicViewsEnabled: true,
    pointSize: 2,
    showNavigationHelpers: true,
    onOrthographicViewsEnabledChange: vi.fn(),
    onPointSizeChange: vi.fn(),
    onToggleNavigationHelpers: vi.fn()
};

describe('SceneViewSettings', () => {
    it('turns off the Top, Side, and Front views', async () => {
        render(SceneViewSettings, { props: defaultProps });
        await fireEvent.click(screen.getByRole('button', { name: 'Scene settings' }));

        const checkbox = screen.getByRole('checkbox', { name: 'Show orthographic projections' });
        expect(checkbox).toBeChecked();
        await fireEvent.click(checkbox);

        expect(defaultProps.onOrthographicViewsEnabledChange).toHaveBeenCalledWith(false);
    });
});
