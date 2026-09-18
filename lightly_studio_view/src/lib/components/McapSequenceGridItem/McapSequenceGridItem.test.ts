import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import McapSequenceGridItem from './McapSequenceGridItem.svelte';

describe('McapSequenceGridItem', () => {
    const defaultProps = { sampleCount: 1, width: 200, height: 200 };

    it('renders a visible placeholder when the sequence has no preview', () => {
        const { getByText } = render(McapSequenceGridItem, { props: defaultProps });

        expect(getByText('MCAP sequence')).toBeInTheDocument();
    });

    it('shows an additional-frame badge only for multi-frame sequences', () => {
        const { queryByTestId } = render(McapSequenceGridItem, {
            props: defaultProps
        });

        expect(queryByTestId('mcap-sequence-frame-count')).not.toBeInTheDocument();

        const { getByTestId } = render(McapSequenceGridItem, {
            props: { ...defaultProps, sampleCount: 5 }
        });

        expect(getByTestId('mcap-sequence-frame-count').textContent?.trim()).toBe('+4');
    });
});
