import { ColorMarker } from '../';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useCustomSourceColors } from '$lib/hooks';
import * as utils from '$lib/utils';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
    useCustomSourceColors().clearCustomColors();
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

    it('gets correct color based on source', () => {
        const mockedColorBySource = vi.spyOn(utils, 'getColorBySource');
        render(ColorMarker, {
            props
        });

        expect(mockedColorBySource).toHaveBeenNthCalledWith(1, props.label, 0.35);
        expect(mockedColorBySource).toHaveBeenNthCalledWith(2, props.label, 1);
        expect(mockedColorBySource).toHaveBeenCalledTimes(2);
    });

    it('uses the correct color', () => {
        type Color = ReturnType<typeof utils.getColorBySource>;
        const colorBorder: Color = {
            color: 'rgba(255, 0, 0, 1)',
            contrastColor: 'rgba(255, 255, 255, 1)'
        };
        const colorBG: Color = {
            color: 'rgba(0, 255, 0, 0.35)',
            contrastColor: 'rgba(0, 0, 0, 0.35)'
        };
        vi.spyOn(utils, 'getColorBySource')
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
        const { getCustomColor } = useCustomSourceColors();
        render(ColorMarker, { props: { ...props, enableColorPicker: true } });

        await fireEvent.click(screen.getByRole('button'));
        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => expect(getCustomColor(props.label)?.color).toBe('#0000ff'));

        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(getCustomColor(props.label)).toBeUndefined();
    });

    it('restores the last applied color when the next preview is cancelled', async () => {
        const { getCustomColor } = useCustomSourceColors();
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

    it('a source color does not change the class color with the same name', async () => {
        useCustomLabelColors().setCustomColor('Predictions', '#111111');
        render(ColorMarker, {
            props: { ...props, label: 'Predictions', enableColorPicker: true }
        });

        await fireEvent.click(screen.getByRole('button'));
        await fireEvent.click(screen.getByTitle('#0000ff'));
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

        expect(useCustomLabelColors().getCustomColor('Predictions')?.color).toBe('#111111');
        expect(useCustomSourceColors().getCustomColor('Predictions')?.color).toBe('#0000ff');
    });
});
