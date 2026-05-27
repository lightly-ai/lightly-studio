import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ClassBalancingForm from './ClassBalancingForm.svelte';

describe('ClassBalancingForm', () => {
    it('does not show the target distribution section when annotation_source is uniform', () => {
        render(ClassBalancingForm, {
            props: {
                params: { annotation_source: 'uniform', target_distribution: [], strength: 1 },
                annotationLabels: [],
                onUpdate: vi.fn()
            }
        });

        expect(screen.queryByTestId('class-balancing-add-row')).not.toBeInTheDocument();
    });

    it('does not show the target distribution section when annotation_source is input', () => {
        render(ClassBalancingForm, {
            props: {
                params: { annotation_source: 'input', target_distribution: [], strength: 1 },
                annotationLabels: [],
                onUpdate: vi.fn()
            }
        });

        expect(screen.queryByTestId('class-balancing-add-row')).not.toBeInTheDocument();
    });

    it('shows the target distribution section when annotation_source is dictionary', () => {
        render(ClassBalancingForm, {
            props: {
                params: { annotation_source: 'dictionary', target_distribution: [], strength: 1 },
                annotationLabels: [],
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('class-balancing-add-row')).toBeInTheDocument();
    });
});
