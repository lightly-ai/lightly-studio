import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import SampleValueBadge from './SampleValueBadge.svelte';

describe('SampleValueBadge', () => {
    it('shows the formatted order value when present', () => {
        render(SampleValueBadge, { props: { orderValue: 0.75 } });
        expect(screen.getByText('0.75')).toBeInTheDocument();
    });

    it('falls back to the similarity score when there is no order value', () => {
        render(SampleValueBadge, { props: { similarityScore: 0.884 } });
        expect(screen.getByText('0.88')).toBeInTheDocument();
    });

    it('prefers the order value over the similarity score', () => {
        render(SampleValueBadge, { props: { orderValue: 4, similarityScore: 0.9 } });
        expect(screen.getByText('4')).toBeInTheDocument();
        expect(screen.queryByText('0.90')).not.toBeInTheDocument();
    });

    it('renders no badge when both values are absent', () => {
        const { container } = render(SampleValueBadge, { props: {} });
        expect(container.querySelector('div')).toBeNull();
    });
});
