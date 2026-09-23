import { ColorMarker } from '../';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import * as utils from '$lib/utils';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
    useCustomLabelColors().clearCustomColors();
});

describe('ColorMarker', () => {
    const testId = 'color-swatch-test';
    const props = {
        label: 'test',
        markerProps: {
            'data-testid': testId
        }
    };

    it('renders marker', () => {
        render(ColorMarker, props);

        expect(screen.getByTestId(testId)).toBeInTheDocument();
    });

    it('gets correct color based on label', () => {
        const mockedColorByLabel = vi.spyOn(utils, 'getColorByLabel');
        render(ColorMarker, {
            props
        });

        expect(mockedColorByLabel).toHaveBeenNthCalledWith(1, props.label, 0.35);
        expect(mockedColorByLabel).toHaveBeenNthCalledWith(2, props.label, 1);
        expect(mockedColorByLabel).toHaveBeenCalledTimes(2);
    });

    it('uses the correct color', () => {
        type Color = ReturnType<typeof utils.getColorByLabel>;
        const colorBorder: Color = {
            color: 'rgba(255, 0, 0, 1)',
            contrastColor: 'rgba(255, 255, 255, 1)'
        };
        const colorBG: Color = {
            color: 'rgba(0, 255, 0, 0.35)',
            contrastColor: 'rgba(0, 0, 0, 0.35)'
        };
        vi.spyOn(utils, 'getColorByLabel')
            .mockReturnValueOnce(colorBG)
            .mockReturnValueOnce(colorBorder);
        render(ColorMarker, {
            props
        });

        const marker = screen.getByTestId(testId);
        expect(marker).toHaveStyle(`background-color: ${colorBG.color};`);
        expect(marker).toHaveStyle(`border-color: ${colorBorder.color}`);
    });

    it('leaves no color override behind when a preview is cancelled', async () => {
        const { getCustomColor } = useCustomLabelColors();
        render(ColorMarker, { props: { ...props, enableColorPicker: true } });

        await fireEvent.click(screen.getByRole('button'));
        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => expect(getCustomColor(props.label)?.color).toBe('#0000ff'));

        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(getCustomColor(props.label)).toBeUndefined();
    });

    it('restores the last applied color when the next preview is cancelled', async () => {
        const { getCustomColor } = useCustomLabelColors();
        render(ColorMarker, { props: { ...props, enableColorPicker: true } });

        await fireEvent.click(screen.getByRole('button'));
        await fireEvent.click(screen.getByTitle('#0000ff'));
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        await fireEvent.click(screen.getByRole('button'));
        await fireEvent.click(screen.getByTitle('#00ff00'));
        await waitFor(() => expect(getCustomColor(props.label)?.color).toBe('#00ff00'));
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(getCustomColor(props.label)?.color).toBe('#0000ff');
    });
});
