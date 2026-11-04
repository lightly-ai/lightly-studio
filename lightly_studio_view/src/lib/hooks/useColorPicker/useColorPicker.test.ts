import { render, screen, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors';
import { getColorByLabel, rgbaToHex } from '$lib/utils';
import UseColorPickerTestWrapper from './useColorPickerTestWrapper.test.svelte';

afterEach(() => {
    useCustomLabelColors().reset();
    useCustomSourceColors().clearCustomColors();
});

describe('useClassColorPicker and useSourceColorPicker', () => {
    describe('without a custom color', () => {
        test('uses getColorByLabel for border (alpha 1) and background (alpha 0.35)', () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            expect(screen.getByTestId('border-color').textContent).toBe(
                getColorByLabel('cat', 1).color
            );
            expect(screen.getByTestId('background-color').textContent).toBe(
                getColorByLabel('cat', 0.35).color
            );
        });

        test('seeds the picker with the palette color in hex and full alpha', () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            expect(screen.getByTestId('initial-color').textContent).toBe(
                rgbaToHex(getColorByLabel('cat', 1).color)
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

            const defaultBorder = getColorByLabel('cat', 1).color;
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

    test('a source picker reads and writes the source store only', async () => {
        useCustomLabelColors().setCustomColor('cat', '#112233');
        render(UseColorPickerTestWrapper, { props: { label: 'cat', kind: 'source' } });
        await tick();
        expect(screen.getByTestId('initial-alpha').textContent).toBe('1');
        expect(screen.getByTestId('border-color').textContent).not.toBe('#112233');

        await fireEvent.click(screen.getByTestId('set-color'));

        expect(useCustomSourceColors().getCustomColor('cat')).toEqual({
            color: '#abcdef',
            alpha: 0.5
        });
        expect(useCustomLabelColors().getCustomColor('cat')?.color).toBe('#112233');
    });

    describe('onCommit', () => {
        const deferred = () => {
            let resolve!: () => void;
            let reject!: (error: Error) => void;
            const promise = new Promise<void>((res, rej) => {
                resolve = res;
                reject = rej;
            });
            return { promise, resolve, reject };
        };
        const colors = () => useCustomLabelColors();

        test('apply calls onCommit with the applied color', async () => {
            const onCommit = vi.fn().mockResolvedValue(undefined);
            render(UseColorPickerTestWrapper, { props: { label: 'cat', onCommit } });

            await fireEvent.click(screen.getByTestId('set-color'));
            await fireEvent.click(screen.getByTestId('apply'));
            await tick();

            expect(onCommit).toHaveBeenCalledExactlyOnceWith({ color: '#abcdef', alpha: 0.5 });
            expect(colors().getSavedColor('cat')).toEqual({ color: '#abcdef', alpha: 0.5 });
        });

        test('shows the preview until onCommit settles', async () => {
            const save = deferred();
            render(UseColorPickerTestWrapper, {
                props: { label: 'cat', onCommit: () => save.promise }
            });

            await fireEvent.click(screen.getByTestId('set-color'));
            await fireEvent.click(screen.getByTestId('apply'));

            expect(colors().getCustomColor('cat')?.color).toBe('#abcdef');
            expect(colors().getSavedColor('cat')).toBeUndefined();

            save.resolve();
            await tick();

            expect(colors().getSavedColor('cat')?.color).toBe('#abcdef');
        });

        test('reverts to the saved color when onCommit rejects', async () => {
            colors().setCustomColor('cat', '#112233');
            render(UseColorPickerTestWrapper, {
                props: { label: 'cat', onCommit: () => Promise.reject(new Error('fail')) }
            });

            await fireEvent.click(screen.getByTestId('set-color'));
            await fireEvent.click(screen.getByTestId('apply'));
            await tick();

            expect(colors().getCustomColor('cat')?.color).toBe('#112233');
            expect(colors().getSavedColor('cat')?.color).toBe('#112233');
        });

        test('reopening while a save is pending keeps the new preview', async () => {
            const save = deferred();
            render(UseColorPickerTestWrapper, {
                props: { label: 'cat', onCommit: () => save.promise }
            });

            await fireEvent.click(screen.getByTestId('set-color'));
            await fireEvent.click(screen.getByTestId('apply'));
            await fireEvent.click(screen.getByTestId('set-other-color'));
            save.resolve();
            await tick();

            expect(colors().getCustomColor('cat')?.color).toBe('#bbbbbb');
            expect(colors().getSavedColor('cat')?.color).toBe('#abcdef');
        });

        test('an older save that resolves late does not overwrite a newer one', async () => {
            const first = deferred();
            const second = deferred();
            const promises = [first.promise, second.promise];
            render(UseColorPickerTestWrapper, {
                props: { label: 'cat', onCommit: () => promises.shift()! }
            });

            await fireEvent.click(screen.getByTestId('set-color'));
            await fireEvent.click(screen.getByTestId('apply'));
            await fireEvent.click(screen.getByTestId('set-other-color'));
            await fireEvent.click(screen.getByTestId('apply'));
            second.resolve();
            await tick();
            first.resolve();
            await tick();

            expect(colors().getSavedColor('cat')?.color).toBe('#bbbbbb');
        });

        test('apply after a store reset acts as cancel', async () => {
            const onCommit = vi.fn().mockResolvedValue(undefined);
            render(UseColorPickerTestWrapper, { props: { label: 'cat', onCommit } });

            await fireEvent.click(screen.getByTestId('set-color'));
            colors().reset();
            await fireEvent.click(screen.getByTestId('apply'));
            await tick();

            expect(onCommit).not.toHaveBeenCalled();
            expect(colors().getCustomColor('cat')).toBeUndefined();
        });
    });

    describe('previews', () => {
        test('cancel keeps a saved color written during the preview', async () => {
            render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            await fireEvent.click(screen.getByTestId('set-color'));
            useCustomLabelColors().setCustomColor('cat', '#112233');
            await fireEvent.click(screen.getByTestId('cancel'));

            expect(useCustomLabelColors().getCustomColor('cat')?.color).toBe('#112233');
        });

        test('unmounting during a preview drops the preview', async () => {
            const { unmount } = render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            await fireEvent.click(screen.getByTestId('set-color'));
            unmount();

            expect(useCustomLabelColors().getCustomColor('cat')).toBeUndefined();
        });

        test('cancel after a rename drops the preview of the old name', async () => {
            const { rerender } = render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            await fireEvent.click(screen.getByTestId('set-color'));
            await rerender({ label: 'kitty' });
            await fireEvent.click(screen.getByTestId('cancel'));

            expect(useCustomLabelColors().getCustomColor('cat')).toBeUndefined();
        });

        test('apply after a rename saves the color under the new name', async () => {
            const { rerender } = render(UseColorPickerTestWrapper, { props: { label: 'cat' } });

            await fireEvent.click(screen.getByTestId('set-color'));
            await rerender({ label: 'kitty' });
            expect(useCustomLabelColors().getCustomColor('kitty')?.color).toBe('#abcdef');
            await fireEvent.click(screen.getByTestId('apply'));
            await tick();

            expect(useCustomLabelColors().getSavedColor('kitty')?.color).toBe('#abcdef');
            expect(useCustomLabelColors().getCustomColor('cat')).toBeUndefined();
        });
    });
});
