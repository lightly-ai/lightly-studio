import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import SampleAnnotations from './index.svelte';

vi.mock('$lib/hooks/useHideAnnotations', () => ({
    useHideAnnotations: () => ({
        isHidden: writable(false),
        handleKeyEvent: vi.fn()
    })
}));

describe('SampleAnnotations', () => {
    it('renders the overlay as pointer-events-none', () => {
        const sample = {
            width: 100,
            height: 80,
            annotations: []
        };

        const { container } = render(SampleAnnotations, {
            props: {
                sample,
                containerWidth: 100,
                containerHeight: 80
            }
        });

        expect(container.querySelector('svg')).toHaveClass('pointer-events-none');
    });
});
