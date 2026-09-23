import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import AnnotationColorLegend from './AnnotationColorLegend.svelte';

const defaultProps = {
    labelName: 'cat',
    className: 'size-4',
    selected: false
};

afterEach(() => {
    useCustomLabelColors().clearCustomColors();
});

describe('AnnotationColorLegend', () => {
    it('leaves no color override behind when a preview is cancelled', async () => {
        const { getCustomColor } = useCustomLabelColors();
        render(AnnotationColorLegend, { props: defaultProps });

        await fireEvent.click(screen.getByRole('button'));
        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => expect(getCustomColor(defaultProps.labelName)?.color).toBe('#0000ff'));

        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(getCustomColor(defaultProps.labelName)).toBeUndefined();
    });
});
