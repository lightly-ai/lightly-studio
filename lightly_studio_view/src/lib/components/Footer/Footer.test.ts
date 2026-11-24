import { render, screen } from '@testing-library/svelte';
import type { Page } from '@sveltejs/kit';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as appState from '$app/state';
import Footer from './Footer.svelte';

describe('Footer', () => {
    beforeEach(() => {
        vi.spyOn(appState, 'page', 'get').mockReturnValue({
            route: { id: '/datasets/[dataset_id]/[collection_type]/[collection_id]/images' }
        } as unknown as Page);
    });

    it('shows how many of the dataset files the grid shows', () => {
        render(Footer, { props: { totalSamples: 128, filteredSamples: 15 } });
        expect(screen.getByText('Showing 15 of 128 images')).toBeDefined();
    });

    it('leaves the dataset total out when it is hidden, as for a labeler', () => {
        render(Footer, { props: { totalSamples: 128, filteredSamples: 15, hideTotal: true } });
        expect(screen.getByText('Showing 15 images')).toBeDefined();
        expect(screen.queryByText(/128/)).toBeNull();
    });

    it('says nothing for a hidden total without files', () => {
        render(Footer, { props: { totalSamples: 128, filteredSamples: 0, hideTotal: true } });
        expect(screen.queryByText(/Showing/)).toBeNull();
    });
});
