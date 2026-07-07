import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import TopNControls from './TopNControls.svelte';
import { CLASS_SORT_LABELS } from '../../topNMatrix';

const defaultProps = {
    n: 5,
    sortBy: 'most-confused' as const,
    maxN: 10
};

describe('TopNControls', () => {
    it('renders the number input bounded by maxN', () => {
        render(TopNControls, { props: { ...defaultProps } });
        const input = screen.getByTestId('class-set-top-n');

        expect(input).toHaveValue(5);
        expect(input).toHaveAttribute('min', '1');
        expect(input).toHaveAttribute('max', '10');
    });

    it('shows the label of the current sort option on the trigger', () => {
        render(TopNControls, { props: { ...defaultProps, sortBy: 'alphabetical' } });

        expect(screen.getByTestId('class-set-sort-by')).toHaveTextContent(
            CLASS_SORT_LABELS['alphabetical']
        );
    });
});
