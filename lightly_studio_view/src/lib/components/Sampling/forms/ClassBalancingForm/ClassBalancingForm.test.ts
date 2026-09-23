import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ClassBalancingForm from './ClassBalancingForm.svelte';

describe('ClassBalancingForm', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('does not show the target distribution section when target_distribution_mode is uniform', () => {
        render(ClassBalancingForm, {
            props: {
                instanceId: 'test',
                params: {
                    annotation_source_id: '',
                    target_distribution_mode: 'uniform',
                    target_distribution: [],
                    strength: 1
                },
                annotationLabels: [],
                onUpdate: vi.fn()
            }
        });

        expect(screen.queryByTestId('class-balancing-add-row')).not.toBeInTheDocument();
    });

    it('does not show the target distribution section when target_distribution_mode is input', () => {
        render(ClassBalancingForm, {
            props: {
                instanceId: 'test',
                params: {
                    annotation_source_id: '',
                    target_distribution_mode: 'input',
                    target_distribution: [],
                    strength: 1
                },
                annotationLabels: [],
                onUpdate: vi.fn()
            }
        });

        expect(screen.queryByTestId('class-balancing-add-row')).not.toBeInTheDocument();
    });

    it('shows the target distribution section when target_distribution_mode is dictionary', () => {
        render(ClassBalancingForm, {
            props: {
                instanceId: 'test',
                params: {
                    annotation_source_id: '',
                    target_distribution_mode: 'dictionary',
                    target_distribution: [],
                    strength: 1
                },
                annotationLabels: [],
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('class-balancing-add-row')).toBeInTheDocument();
    });

    it('keeps the target distribution when the annotation source changes', async () => {
        const onUpdate = vi.fn();

        render(ClassBalancingForm, {
            props: {
                instanceId: 'test',
                params: {
                    annotation_source_id: 'source-1',
                    target_distribution_mode: 'dictionary',
                    target_distribution: [{ class_name: 'cat', weight: 0.5 }],
                    strength: 1
                },
                annotationLabels: ['cat', 'dog'],
                annotationSourceOptions: [
                    { id: 'source-1', name: 'ground-truth' },
                    { id: 'source-2', name: 'predictions' }
                ],
                onUpdate
            }
        });

        await fireEvent.keyDown(screen.getByTestId('annotation-source-trigger'), { key: 'Enter' });
        await fireEvent.pointerUp(
            await screen.findByTestId('annotation-source-option-predictions')
        );

        expect(onUpdate).toHaveBeenCalledWith({ annotation_source_id: 'source-2' });
    });
});
