import { render, screen } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useDefaultSource } from '$lib/hooks/useDefaultSource/useDefaultSource';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import Wrapper from './useAnnotationTargetTestWrapper.test.svelte';

const mocks = vi.hoisted(() => ({
    sources: [] as { collection_id: string; name: string }[]
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: mocks.sources })
}));

const setup = () => {
    let context!: AnnotationLabelContext;
    render(Wrapper, { props: { onContext: (value) => (context = value) } });
    return { context };
};

describe('useAnnotationTarget', () => {
    beforeEach(() => {
        mocks.sources = [
            { collection_id: 's1', name: 'labels' },
            { collection_id: 's2', name: 'predictions' }
        ];
        useDefaultSource().setDefaultSource('col-1', null);
        useGlobalStorage().lastAnnotationSource.set({});
    });

    it('seeds the default source', () => {
        useDefaultSource().setDefaultSource('col-1', 'predictions');

        setup();

        expect(screen.getByTestId('target-source')).toHaveTextContent('predictions');
    });

    it('follows a default set while the page is open', () => {
        setup();
        expect(screen.getByTestId('target-source')).toHaveTextContent('none');

        useDefaultSource().setDefaultSource('col-1', 'labels');
        flushSync();

        expect(screen.getByTestId('target-source')).toHaveTextContent('labels');
    });

    it('does not let a new default replace a picked source', () => {
        const { context } = setup();
        context.annotationSource = 'predictions';
        flushSync();

        useDefaultSource().setDefaultSource('col-1', 'labels');
        flushSync();

        expect(screen.getByTestId('target-source')).toHaveTextContent('predictions');
    });

    it('follows a rename of the seeded default', () => {
        useDefaultSource().setDefaultSource('col-1', 'labels');
        const { context } = setup();
        expect(context.annotationSource).toBe('labels');

        mocks.sources = [
            { collection_id: 's1', name: 'labels_v2' },
            { collection_id: 's2', name: 'predictions' }
        ];
        useDefaultSource().renameDefaultSource('col-1', 'labels', 'labels_v2');
        flushSync();

        expect(context.annotationSource).toBe('labels_v2');
    });

    it('keeps a remembered pick when the default changes', () => {
        useDefaultSource().setDefaultSource('col-1', 'labels');
        useGlobalStorage().updateLastAnnotationSource('col-1', 'labels');
        const { context } = setup();

        useDefaultSource().setDefaultSource('col-1', 'predictions');
        flushSync();

        expect(context.annotationSource).toBe('labels');
    });
});
