import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import AnnotationEgoDistance from './AnnotationEgoDistance.svelte';

describe('AnnotationEgoDistance', () => {
    it('shows the distance of a cuboid within the range', () => {
        render(AnnotationEgoDistance, { props: { meters: 38.24, isBeyondRange: false } });

        expect(screen.getByText('Ego distance:')).toBeInTheDocument();
        expect(screen.getByTestId('point-cloud-annotation-distance')).toHaveTextContent('38.2 m');
        expect(screen.queryByText('beyond range')).not.toBeInTheDocument();
    });

    it('marks a cuboid beyond the range', () => {
        render(AnnotationEgoDistance, { props: { meters: 52, isBeyondRange: true } });

        expect(screen.getByTestId('point-cloud-annotation-distance')).toHaveTextContent('52.0 m');
        expect(screen.getByText('beyond range')).toBeInTheDocument();
    });
});
