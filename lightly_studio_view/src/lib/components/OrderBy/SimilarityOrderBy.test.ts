import { fireEvent, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import { useSimilaritySort } from '$lib/hooks/useSimilaritySort';
import SimilarityOrderBy from './SimilarityOrderBy.svelte';

describe('SimilarityOrderBy', () => {
    beforeEach(() => {
        useSimilaritySort().resetOnNewSearch({});
    });

    it('shows similarity as a locked field', () => {
        render(SimilarityOrderBy);

        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('Similarity');
        expect(screen.getByTestId('sort-by-trigger')).toBeDisabled();
    });

    it('toggles the similarity direction', async () => {
        const user = userEvent.setup();
        render(SimilarityOrderBy);
        const button = screen.getByTestId('sort-direction-button');

        await user.hover(button);
        expect(screen.getByRole('tooltip')).toHaveTextContent('Sort descending');

        await fireEvent.click(button);

        expect(get(useSimilaritySort().direction)).toBe(SortDirection.ASC);
    });
});
