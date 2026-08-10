import { render, screen, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { getColorByLabel, rgbaToHex } from '$lib/utils';
import UseColorPickerTestWrapper from './useColorPickerTestWrapper.test.svelte';

afterEach(() => {
    useCustomLabelColors().clearCustomColors();
});

describe('useColorPicker', () => {
    describe('without a custom color', () => {
        it('uses getColorByLabel for border (alpha 1) and background (alpha 0.35)', () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            expect(screen.getByTestId('border-color').textContent).toBe(
                getColorByLabel('cat', 1).color
            );
            expect(screen.getByTestId('background-color').textContent).toBe(
                getColorByLabel('cat', 0.35).color
            );
        });

        it('seeds the picker with the palette color in hex and full alpha', () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            expect(screen.getByTestId('initial-color').textContent).toBe(
                rgbaToHex(getColorByLabel('cat', 1).color)
            );
            expect(screen.getByTestId('initial-alpha').textContent).toBe('1');
        });
    });

    describe('with a custom color', () => {
        it('border uses the override hex; background applies override alpha × 0.35', async () => {
            useCustomLabelColors().setCustomColor('cat', '#ff8040', 0.8);

            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });
            await tick();

            expect(screen.getByTestId('border-color').textContent).toBe('#ff8040');
            expect(screen.getByTestId('background-color').textContent).toBe(
                `rgba(255, 128, 64, ${0.8 * 0.35})`
            );
        });

        it('seeds the picker with the override hex and override alpha', async () => {
            useCustomLabelColors().setCustomColor('cat', '#ff8040', 0.8);

            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });
            await tick();

            expect(screen.getByTestId('initial-color').textContent).toBe('#ff8040');
            expect(screen.getByTestId('initial-alpha').textContent).toBe('0.8');
        });

        it('reacts when the custom color is added after mount', async () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            const defaultBorder = getColorByLabel('cat', 1).color;
            expect(screen.getByTestId('border-color').textContent).toBe(defaultBorder);

            useCustomLabelColors().setCustomColor('cat', '#112233', 1);
            await tick();

            expect(screen.getByTestId('border-color').textContent).toBe('#112233');
        });
    });

    it('setColor persists the picked value against the current label', async () => {
        render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

        await fireEvent.click(screen.getByTestId('set-color'));

        const stored = useCustomLabelColors().getCustomColor('cat');
        expect(stored).toEqual({ color: '#abcdef', alpha: 0.5 });
    });

    it('removes a preview when the label had no custom color', async () => {
        render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

        await fireEvent.click(screen.getByTestId('set-color'));
        await fireEvent.click(screen.getByTestId('cancel-color'));

        expect(useCustomLabelColors().getCustomColor('cat')).toBeUndefined();
    });

    it('restores the custom color that existed before a preview', async () => {
        const customColors = useCustomLabelColors();
        customColors.setCustomColor('cat', '#112233', 0.75);
        render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

        await fireEvent.click(screen.getByTestId('set-color'));
        await fireEvent.click(screen.getByTestId('cancel-color'));

        expect(customColors.getCustomColor('cat')).toEqual({ color: '#112233', alpha: 0.75 });
    });

    it('uses the applied color as the baseline for the next preview', async () => {
        const customColors = useCustomLabelColors();
        render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

        await fireEvent.click(screen.getByTestId('set-color'));
        await fireEvent.click(screen.getByTestId('apply-color'));
        await fireEvent.click(screen.getByTestId('set-alternate-color'));
        await fireEvent.click(screen.getByTestId('cancel-color'));

        expect(customColors.getCustomColor('cat')).toEqual({ color: '#abcdef', alpha: 0.5 });
    });
});
