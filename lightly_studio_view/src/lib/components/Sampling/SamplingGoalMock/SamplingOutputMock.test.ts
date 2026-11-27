import { fireEvent, render, screen } from '@testing-library/svelte';
import SamplingOutputMock from './SamplingOutputMock.svelte';
import SamplingGoalMock from './SamplingGoalMock.svelte';

describe('SamplingOutputMock', () => {
    it('reviews the chosen output before confirming the preview', async () => {
        render(SamplingOutputMock, { props: { goalTitle: 'Select a diverse subset' } });

        await fireEvent.input(screen.getByLabelText('Number of samples wanted'), {
            target: { value: '25' }
        });
        await fireEvent.input(screen.getByLabelText('Resulting tag'), {
            target: { value: 'Varied images' }
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Review selection' }));

        expect(screen.getByRole('status')).toHaveTextContent(
            'Review: select 25 samples using “Select a diverse subset” and save them as “Varied images”.'
        );

        await fireEvent.click(screen.getByRole('button', { name: 'Confirm preview' }));
        expect(screen.getByRole('status')).toHaveTextContent('No selection was created.');
    });

    it('reviews deduplication with an optional maximum instead of an exact count', async () => {
        render(SamplingOutputMock, {
            props: { goalTitle: 'Remove near-duplicates', isDeduplication: true }
        });

        expect(screen.queryByLabelText('Number of samples wanted')).not.toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Review selection' }));
        expect(screen.getByRole('status')).toHaveTextContent(
            'keep distinct images with no maximum'
        );

        await fireEvent.input(screen.getByLabelText('Maximum images to keep (optional)'), {
            target: { value: '25' }
        });
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Review selection' }));
        expect(screen.getByRole('status')).toHaveTextContent('keep up to 25 images');

        await fireEvent.input(screen.getByLabelText('Maximum images to keep (optional)'), {
            target: { value: '0' }
        });
        expect(screen.getByRole('button', { name: 'Review selection' })).toBeDisabled();
    });
});

describe('SamplingGoalMock', () => {
    it('requires another review after changing goal settings', async () => {
        render(SamplingGoalMock);
        await fireEvent.click(screen.getByRole('button', { name: 'Review selection' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Confirm preview' }));

        await fireEvent.change(screen.getByLabelText('Diversity based on'), {
            target: { value: 'objects' }
        });

        expect(screen.queryByRole('status')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Review selection' })).toBeEnabled();
        expect(screen.getByLabelText('Number of samples wanted')).toHaveValue(100);
    });
});
