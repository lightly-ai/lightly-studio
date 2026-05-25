import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import SelectionSummary from './SelectionSummary.svelte';

describe('SelectionSummary', () => {
    it('does not render when fewer than two strategies are active', () => {
        render(SelectionSummary, {
            props: {
                strategyLabels: ['Diversity']
            }
        });

        expect(screen.queryByTestId('selection-summary')).not.toBeInTheDocument();
    });

    it('renders a summary when multiple strategies are active', () => {
        render(SelectionSummary, {
            props: {
                strategyLabels: ['Diversity', 'Typicality', 'Class Balancing']
            }
        });

        expect(screen.getByTestId('selection-summary')).toHaveTextContent(
            'Selection will combine 3 strategies: Diversity, Typicality, Class Balancing.'
        );
    });
});
