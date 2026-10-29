import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import TrainWithLightlyTrain from './TrainWithLightlyTrain.svelte';
import { LIGHTLYTRAIN_SNIPPET, TRAIN_WITH_LIGHTLYTRAIN_DOCS_URL } from './lightlyTrainSnippet';

describe('TrainWithLightlyTrain', () => {
    it('copies the snippet and links to the docs page', async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.assign(navigator, { clipboard: { writeText } });
        render(TrainWithLightlyTrain);

        await fireEvent.click(screen.getByRole('button', { name: 'Copy code' }));

        expect(writeText).toHaveBeenCalledWith(LIGHTLYTRAIN_SNIPPET);
        await waitFor(() => expect(screen.getByRole('button', { name: 'Copied' })).toBeVisible());
        expect(
            screen.getByRole('link', { name: 'Train a detector with LightlyTrain' })
        ).toHaveAttribute('href', TRAIN_WITH_LIGHTLYTRAIN_DOCS_URL);
    });
});
