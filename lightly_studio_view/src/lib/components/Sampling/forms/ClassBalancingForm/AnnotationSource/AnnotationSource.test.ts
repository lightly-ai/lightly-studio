import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AnnotationSource from './AnnotationSource.svelte';

describe('AnnotationSource', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows the current annotation source label', () => {
        render(AnnotationSource, {
            props: {
                annotationSource: 'uniform',
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('class-balancing-annotation-source')).toHaveTextContent(
            'Uniform'
        );
    });

    it('shows all annotation source options when the trigger is clicked', async () => {
        render(AnnotationSource, {
            props: {
                annotationSource: 'uniform',
                onUpdate: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-annotation-source'), {
            key: 'Enter'
        });

        expect(
            await screen.findByTestId('class-balancing-annotation-source-uniform')
        ).toBeInTheDocument();
        expect(screen.getByTestId('class-balancing-annotation-source-input')).toBeInTheDocument();
        expect(
            screen.getByTestId('class-balancing-annotation-source-dictionary')
        ).toBeInTheDocument();
    });

    it('calls onUpdate with the selected annotation source', async () => {
        const onUpdate = vi.fn();

        render(AnnotationSource, {
            props: {
                annotationSource: 'uniform',
                onUpdate
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-annotation-source'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(
            await screen.findByTestId('class-balancing-annotation-source-input')
        );

        expect(onUpdate).toHaveBeenCalledWith('input');
    });
});
