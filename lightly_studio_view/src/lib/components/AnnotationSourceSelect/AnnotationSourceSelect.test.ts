import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AnnotationSourceSelect from './AnnotationSourceSelect.svelte';

describe('AnnotationSourceSelect', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    const defaultProps = {
        sourceNames: ['ground_truth', 'predictions'],
        onSelect: vi.fn()
    };

    it('shows a placeholder when no source is selected', () => {
        render(AnnotationSourceSelect, { props: { ...defaultProps } });

        expect(screen.getByTestId('annotation-source-trigger')).toHaveTextContent(
            'Select a source...'
        );
    });

    it('shows the currently selected source', () => {
        render(AnnotationSourceSelect, {
            props: { ...defaultProps, selectedSource: 'predictions' }
        });

        expect(screen.getByTestId('annotation-source-trigger')).toHaveTextContent('predictions');
    });

    it('calls onSelect with the chosen source name', async () => {
        const onSelect = vi.fn();
        render(AnnotationSourceSelect, { props: { ...defaultProps, onSelect } });

        await fireEvent.keyDown(screen.getByTestId('annotation-source-trigger'), { key: 'Enter' });
        await fireEvent.pointerUp(
            await screen.findByTestId('annotation-source-option-predictions')
        );

        expect(onSelect).toHaveBeenCalledWith('predictions');
    });
});
