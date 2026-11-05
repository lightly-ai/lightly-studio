import { render, screen } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { get, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { AnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { LOADING_SOURCES_MESSAGE, PICK_SOURCE_MESSAGE } from './messages';
import Wrapper from './useAnnotationTargetTestWrapper.test.svelte';

type Source = { collection_id: string; name: string };

// The query data is a store, so the hook reacts when a test changes the source list.
const mocks = vi.hoisted(() => ({
    sources: null as unknown as Writable<Source[] | undefined>
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', async () => {
    const { writable, fromStore } = await import('svelte/store');
    mocks.sources = writable(undefined);
    const sources = fromStore(mocks.sources);
    return {
        useAnnotationCollections: () => ({
            get data() {
                return sources.current;
            },
            isError: false
        })
    };
});

const setSources = (...names: string[]) => {
    mocks.sources.set(names.map((name, index) => ({ collection_id: `s${index}`, name })));
    flushSync();
};

const setup = (props: { annotations?: AnnotationView[]; hiddenIds?: Set<string> } = {}) => {
    let context!: AnnotationLabelContext;
    let pick!: (name: string, options?: { isNew?: boolean }) => void;
    render(Wrapper, {
        props: {
            ...props,
            onReady: (value, setTargetSource) => {
                context = value;
                pick = (name, options) => {
                    setTargetSource(name, options);
                    flushSync();
                };
            }
        }
    });
    return { context, pick };
};

const target = () => screen.getByTestId('target-source');
const storedPick = () => get(useGlobalStorage().lastAnnotationSource)['col-1'];

describe('useAnnotationTarget', () => {
    beforeEach(() => {
        setSources('labels', 'predictions');
        useGlobalStorage().lastAnnotationSource.set({});
    });

    it('blocks new annotations until the sources load, without assuming a target', () => {
        useGlobalStorage().updateLastAnnotationSource('col-1', 'labels');
        mocks.sources.set(undefined);
        const { context } = setup();

        expect(target()).toHaveTextContent('none');
        expect(context.annotationSourceBlockedReason).toBe(LOADING_SOURCES_MESSAGE);

        setSources('labels', 'predictions');

        expect(target()).toHaveTextContent('labels');
        expect(context.annotationSourceBlockedReason).toBeNull();
    });

    it('drops a remembered pick whose source was deleted elsewhere', () => {
        useGlobalStorage().updateLastAnnotationSource('col-1', 'review');
        const { context } = setup();

        expect(context.annotationSource).toBeNull();
        expect(context.annotationSourceBlockedReason).toBe(PICK_SOURCE_MESSAGE);
    });

    it('clears a target deleted while the page is open', () => {
        setSources('labels', 'predictions', 'review');
        const { context, pick } = setup();
        pick('review');

        setSources('labels', 'predictions');

        expect(context.annotationSource).toBeNull();
        expect(storedPick()).toBeUndefined();
        expect(context.annotationSourceBlockedReason).toBe(PICK_SOURCE_MESSAGE);
    });

    it('asks for a source again after the picked source is renamed elsewhere', () => {
        const { context, pick } = setup();
        pick('labels');

        // A rename and a delete plus an unrelated create look the same from here.
        setSources('labels_v2', 'predictions');

        expect(context.annotationSource).toBeNull();
        expect(storedPick()).toBeUndefined();
        expect(context.annotationSourceBlockedReason).toBe(PICK_SOURCE_MESSAGE);
    });

    it('follows a rename of the only source', () => {
        setSources('labels');
        const { context } = setup();
        expect(context.annotationSource).toBe('labels');

        setSources('ground_truth');

        expect(target()).toHaveTextContent('ground_truth');
    });

    it('keeps a typed new source picked when the list changes', () => {
        const { context, pick } = setup();
        pick('review', { isNew: true });

        setSources('labels', 'predictions', 'other');

        expect(context.annotationSource).toBe('review');
    });

    it('blocks a hidden target and refuses to pick a hidden source', () => {
        const annotations = [
            { sample_id: 'a1', annotation_collection_id: 's0', annotation_type: 'object_detection' }
        ] as AnnotationView[];
        useGlobalStorage().updateLastAnnotationSource('col-1', 'labels');
        const { context, pick } = setup({ annotations, hiddenIds: new Set(['a1']) });

        expect(context.hiddenAnnotationSources).toEqual(['labels']);
        expect(context.annotationSourceBlockedReason).toContain('labels is hidden');

        pick('predictions');
        pick('labels');

        expect(context.annotationSource).toBe('predictions');
    });
});
