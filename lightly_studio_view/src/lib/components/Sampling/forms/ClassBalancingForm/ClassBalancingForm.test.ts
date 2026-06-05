import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ClassBalancingForm from './ClassBalancingForm.svelte';

describe('ClassBalancingForm', () => {
    it('does not show the target distribution section when target_distribution_mode is uniform', () => {
        render(ClassBalancingForm, {
            props: {
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
});
