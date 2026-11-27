import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import EgoRangeSettings from './EgoRangeSettings.svelte';

const defaultProps = {
    enabled: false,
    radius: 40,
    egoFrame: 'CABIN',
    egoFrameOptions: ['map', 'CABIN'],
    onEnabledChange: vi.fn(),
    onRadiusChange: vi.fn(),
    onEgoFrameChange: vi.fn()
};

describe('EgoRangeSettings', () => {
    it('turns on the ego range', async () => {
        render(EgoRangeSettings, { props: defaultProps });

        const checkbox = screen.getByRole('checkbox', { name: 'Show ego range' });
        expect(checkbox).not.toBeChecked();
        expect(screen.queryByLabelText('Radius (m)')).not.toBeInTheDocument();
        await fireEvent.click(checkbox);

        expect(defaultProps.onEnabledChange).toHaveBeenCalledWith(true);
    });

    it('changes the radius', async () => {
        render(EgoRangeSettings, { props: { ...defaultProps, enabled: true } });

        await fireEvent.change(screen.getByLabelText('Radius (m)'), { target: { value: '25' } });

        expect(defaultProps.onRadiusChange).toHaveBeenCalledWith(25);
    });

    it('keeps the radius when the field is cleared', async () => {
        const onRadiusChange = vi.fn();
        render(EgoRangeSettings, { props: { ...defaultProps, enabled: true, onRadiusChange } });

        await fireEvent.change(screen.getByLabelText('Radius (m)'), { target: { value: '' } });

        expect(onRadiusChange).not.toHaveBeenCalled();
    });

    it('changes the ego frame', async () => {
        render(EgoRangeSettings, { props: { ...defaultProps, enabled: true } });

        await fireEvent.change(screen.getByLabelText('Ego frame'), {
            target: { value: 'map' }
        });

        expect(defaultProps.onEgoFrameChange).toHaveBeenCalledWith('map');
    });
});
