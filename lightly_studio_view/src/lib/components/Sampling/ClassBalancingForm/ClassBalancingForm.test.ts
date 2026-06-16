import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ClassBalancingForm from './ClassBalancingForm.svelte';

describe('ClassBalancingForm', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows the current balancing mode label', () => {
        render(ClassBalancingForm, {
            props: {
                balancingMode: 'uniform',
                annotationCollections: [],
                annotationSourceId: '',
                onBalancingModeChange: vi.fn(),
                onAnnotationSourceChange: vi.fn()
            }
        });

        expect(screen.getByTestId('sampling-dialog-balancing-mode-select')).toHaveTextContent(
            'Uniform'
        );
    });

    it('shows the uniform option in the dropdown', async () => {
        render(ClassBalancingForm, {
            props: {
                balancingMode: 'uniform',
                annotationCollections: [],
                annotationSourceId: '',
                onBalancingModeChange: vi.fn(),
                onAnnotationSourceChange: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('sampling-balancing-mode-uniform')).toBeInTheDocument();
    });

    it('shows input balancing mode as disabled and coming soon', async () => {
        render(ClassBalancingForm, {
            props: {
                balancingMode: 'uniform',
                annotationCollections: [],
                annotationSourceId: '',
                onBalancingModeChange: vi.fn(),
                onAnnotationSourceChange: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });

        const inputOption = await screen.findByTestId('sampling-balancing-mode-input');
        expect(inputOption).toHaveAttribute('data-disabled');
        expect(inputOption).toHaveTextContent('Input (Coming soon)');
    });

    it('wires the annotation source label to the select trigger', () => {
        render(ClassBalancingForm, {
            props: {
                balancingMode: 'uniform',
                annotationCollections: [
                    {
                        collection_id: 'annotation-source-1',
                        name: 'Ground Truth'
                    }
                ],
                annotationSourceId: 'annotation-source-1',
                onBalancingModeChange: vi.fn(),
                onAnnotationSourceChange: vi.fn()
            }
        });

        const trigger = screen.getByTestId('annotation-source-trigger');
        expect(screen.getByLabelText('Annotation Source')).toBe(trigger);
    });
});
