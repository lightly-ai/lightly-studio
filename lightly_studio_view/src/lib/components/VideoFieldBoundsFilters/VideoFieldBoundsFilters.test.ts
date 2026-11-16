import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { tick } from 'svelte';
import { useVideoBounds } from '$lib/hooks';
import VideoFieldBoundsFilters from './VideoFieldBoundsFilters.svelte';

vi.mock('$app/state', () => ({ page: { params: {} } }));
const storage = useVideoBounds();
const bounds = {
    width: { min: 0, max: 1000 },
    height: { min: 0, max: 1000 },
    fps: { min: 0, max: 60 },
    duration_s: { min: 0, max: 120 }
};
afterEach(() => {
    storage.videoBounds.set(null);
    storage.videoBoundsValues.set(null);
});

it.each([
    ['width', 'Width', '250'],
    ['height', 'Height', '250'],
    ['fps', 'FPS', '29.970029'],
    ['duration_s', 'Duration', '12.3456789']
] as const)(
    'preserves exact %s values when moving the opposite slider',
    async (key, label, input) => {
        storage.updateVideoBounds(bounds);
        storage.updateVideoBoundsValues(bounds);
        const onFilterChanged = vi.fn();
        render(VideoFieldBoundsFilters, { onFilterChanged });
        const minimum = screen.getByRole('textbox', { name: `${label} minimum` });
        await fireEvent.input(minimum, { target: { value: input } });
        await fireEvent.blur(minimum);
        expect(get(storage.videoBoundsValues)?.[key].min).toBe(Number(input));
        expect(onFilterChanged).toHaveBeenCalledExactlyOnceWith(
            key,
            Number(input),
            bounds[key].max
        );
        const index = Object.keys(bounds).indexOf(key);
        await fireEvent.keyDown(screen.getAllByRole('slider')[index * 2 + 1], { key: 'ArrowLeft' });
        expect(get(storage.videoBoundsValues)?.[key].min).toBe(Number(input));
        expect(minimum).toHaveValue(input);
        const maximum = screen.getByRole('textbox', { name: `${label} maximum` });
        await fireEvent.input(maximum, { target: { value: input } });
        await fireEvent.blur(maximum);
        expect(get(storage.videoBoundsValues)?.[key]).toEqual({
            min: Number(input),
            max: Number(input)
        });
        expect(maximum).toBeInTheDocument();
        storage.updateVideoBoundsValues(bounds);
        await tick();
        expect(minimum).toHaveValue('0');
    }
);
