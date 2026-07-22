import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ManualClassSelector from './ManualClassSelector.svelte';

const allClasses = ['cat', 'dog', 'bird'];

const defaultProps = {
    selected: ['cat'],
    allClasses
};

describe('ManualClassSelector', () => {
    it('shows the selected count and lists every class', () => {
        render(ManualClassSelector, { props: { ...defaultProps } });

        expect(screen.getByText('1 of 3 selected')).toBeInTheDocument();
        for (const className of allClasses) {
            expect(screen.getByText(className)).toBeInTheDocument();
        }
    });

    it('selects every class when "Select all" is clicked', async () => {
        render(ManualClassSelector, { props: { ...defaultProps } });

        await fireEvent.click(screen.getByText('Select all'));

        await waitFor(() => expect(screen.getByText('3 of 3 selected')).toBeInTheDocument());
    });

    it('clears the selection when "Clear" is clicked', async () => {
        render(ManualClassSelector, { props: { ...defaultProps } });

        await fireEvent.click(screen.getByText('Clear'));

        await waitFor(() => expect(screen.getByText('0 of 3 selected')).toBeInTheDocument());
    });

    it('applies the given search test-id to the input', () => {
        render(ManualClassSelector, { props: { ...defaultProps, searchTestId: 'my-search' } });

        expect(screen.getByTestId('my-search')).toBeInTheDocument();
    });
});
