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

    it('keeps full opacity when Apply is clicked without changes', async () => {
        const { getCustomColor } = useCustomLabelColors();
        render(AnnotationColorLegend, { props: defaultProps });

        await fireEvent.click(screen.getByRole('button', { name: 'Change the color of cat' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

        expect(getCustomColor(defaultProps.labelName)?.alpha).toBe(1);
    });

    it('names the picker button after the class', () => {
        render(AnnotationColorLegend, { props: defaultProps });

        expect(screen.getByRole('button', { name: 'Change the color of cat' })).toBeInTheDocument();
    });
});
