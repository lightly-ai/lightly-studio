import { ColorMarker } from '../';
import * as utils from '$lib/utils';
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

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
        const mockedColorByLabel = vi.spyOn(utils, 'computeColorByKey');
        render(ColorMarker, {
            props
        });

        expect(mockedColorByLabel).toHaveBeenNthCalledWith(1, props.label, 0.35);
        expect(mockedColorByLabel).toHaveBeenNthCalledWith(2, props.label, 1);
        expect(mockedColorByLabel).toHaveBeenCalledTimes(2);
    });

    it('uses the correct color', () => {
        type Color = ReturnType<typeof utils.computeColorByKey>;
        const colorBorder: Color = {
            color: 'rgba(255, 0, 0, 1)',
            contrastColor: 'rgba(255, 255, 255, 1)'
        };
        const colorBG: Color = {
            color: 'rgba(0, 255, 0, 0.35)',
            contrastColor: 'rgba(0, 0, 0, 0.35)'
        };
        vi.spyOn(utils, 'computeColorByKey')
            .mockReturnValueOnce(colorBG)
            .mockReturnValueOnce(colorBorder);
        render(ColorMarker, {
            props
        });

        const marker = screen.getByTestId(testId);
        expect(marker).toHaveStyle(`background-color: ${colorBG.color};`);
        expect(marker).toHaveStyle(`border-color: ${colorBorder.color}`);
    });
});
