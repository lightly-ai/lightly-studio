import { render, screen, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, describe, expect, test } from 'vitest';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { computeColorByKey, rgbaToHex } from '$lib/utils';
import UseColorPickerTestWrapper from './useColorPickerTestWrapper.test.svelte';

afterEach(() => {
    useCustomLabelColors().clearCustomColors();
});

describe('useColorPicker', () => {
    describe('without a custom color', () => {
        test('uses computeColorByKey for border (alpha 1) and background (alpha 0.35)', () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            expect(screen.getByTestId('border-color').textContent).toBe(
                computeColorByKey('cat', 1).color
            );
            expect(screen.getByTestId('background-color').textContent).toBe(
                computeColorByKey('cat', 0.35).color
            );
        });

        test('seeds the picker with the palette color in hex and full alpha', () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            expect(screen.getByTestId('initial-color').textContent).toBe(
                rgbaToHex(computeColorByKey('cat', 1).color)
            );
            expect(screen.getByTestId('initial-alpha').textContent).toBe('1');
        });
    });

    describe('with a custom color', () => {
        test('border uses the override hex; background applies override alpha × 0.35', async () => {
            useCustomLabelColors().setCustomColor('cat', '#ff8040', 0.8);

            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });
            await tick();

            expect(screen.getByTestId('border-color').textContent).toBe('#ff8040');
            expect(screen.getByTestId('background-color').textContent).toBe(
                `rgba(255, 128, 64, ${0.8 * 0.35})`
            );
        });

        test('seeds the picker with the override hex and override alpha', async () => {
            useCustomLabelColors().setCustomColor('cat', '#ff8040', 0.8);

            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });
            await tick();

            expect(screen.getByTestId('initial-color').textContent).toBe('#ff8040');
            expect(screen.getByTestId('initial-alpha').textContent).toBe('0.8');
        });

        test('reacts when the custom color is added after mount', async () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            const defaultBorder = computeColorByKey('cat', 1).color;
            expect(screen.getByTestId('border-color').textContent).toBe(defaultBorder);

            useCustomLabelColors().setCustomColor('cat', '#112233', 1);
            await tick();

            expect(screen.getByTestId('border-color').textContent).toBe('#112233');
        });
    });

    test('setColor persists the picked value against the current label', async () => {
        render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

        await fireEvent.click(screen.getByTestId('set-color'));

        const stored = useCustomLabelColors().getCustomColor('cat');
        expect(stored).toEqual({ color: '#abcdef', alpha: 0.5 });
    });
});
