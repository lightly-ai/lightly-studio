import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import CollectionLayoutFooter from './CollectionLayoutFooter.svelte';
import '@testing-library/jest-dom';

// Mock the Footer component
vi.mock('$lib/components', () => ({
    Footer: () => ({})
}));

describe('CollectionLayoutFooter', () => {
    it('renders without crashing', () => {
        expect(() => {
            render(CollectionLayoutFooter, {
                props: {
                    totalSamples: 100,
                    filteredSamples: 50,
                    totalAnnotations: 200,
                    filteredAnnotations: 75
                }
            });
        }).not.toThrow();
    });

    it('accepts undefined values for filtered counts', () => {
        const { component } = render(CollectionLayoutFooter, {
            props: {
                totalSamples: 100,
                filteredSamples: undefined,
                totalAnnotations: 200,
                filteredAnnotations: undefined
            }
        });

        expect(component).toBeTruthy();
    });

    it('accepts all numeric values', () => {
        const { component } = render(CollectionLayoutFooter, {
            props: {
                totalSamples: 1000,
                filteredSamples: 500,
                totalAnnotations: 2000,
                filteredAnnotations: 1500
            }
        });

        expect(component).toBeTruthy();
    });
});
