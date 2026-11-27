import { flushSync } from 'svelte';
import { get, writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCuboidTargetSource } from './useCuboidTargetSource.svelte';

const { lastAnnotationSource } = vi.hoisted(() => ({
    lastAnnotationSource: { store: null as unknown as ReturnType<typeof writable> }
}));

vi.mock('$lib/hooks/useGlobalStorage', async () => {
    const { writable } = await import('svelte/store');
    lastAnnotationSource.store = writable<Record<string, string>>({});
    const store = lastAnnotationSource.store as ReturnType<typeof writable<Record<string, string>>>;
    return {
        useGlobalStorage: () => ({
            lastAnnotationSource: store,
            updateLastAnnotationSource: (collectionId: string, name: string) =>
                store.update((value) => ({ ...value, [collectionId]: name })),
            removeLastAnnotationSource: (collectionId: string, name: string) =>
                store.update((value) => {
                    if (value[collectionId] !== name) return value;
                    const next = { ...value };
                    delete next[collectionId];
                    return next;
                })
        })
    };
});

let dispose = () => {};
afterEach(() => dispose());
beforeEach(() => lastAnnotationSource.store.set({}));

function setup(initialNames: string[] = ['labels', 'predictions']) {
    const input = $state({ collectionId: 'c1', names: initialNames as string[] | undefined });
    let target!: ReturnType<typeof useCuboidTargetSource>;
    dispose = $effect.root(() => {
        target = useCuboidTargetSource({
            getCollectionId: () => input.collectionId,
            getSourceNames: () => input.names,
            getIsError: () => false
        });
    });
    flushSync();
    return { input, target };
}

describe('useCuboidTargetSource', () => {
    it('remembers a picked source for the collection', () => {
        const { target } = setup();
        target.setTarget('labels');
        flushSync();
        expect(get(lastAnnotationSource.store)).toEqual({ c1: 'labels' });
        expect(target.targetSource).toBe('labels');
        expect(target.needsPick).toBe(false);
    });

    it('targets a typed new source before it exists', () => {
        const { target } = setup();
        target.setTarget(' review ', { isNew: true });
        flushSync();
        expect(target.targetSource).toBe('review');
        expect(target.typedSource).toBe('review');
    });

    it('ignores a blank name', () => {
        const { target } = setup();
        target.setTarget('  ');
        flushSync();
        expect(get(lastAnnotationSource.store)).toEqual({});
        expect(target.needsPick).toBe(true);
    });

    it('forgets a pick whose source was renamed elsewhere', () => {
        const { input, target } = setup();
        target.setTarget('labels');
        flushSync();
        input.names = ['labels_v2', 'predictions'];
        flushSync();
        expect(get(lastAnnotationSource.store)).toEqual({});
        expect(target.needsPick).toBe(true);
    });

    it('does not carry a typed name to another collection', () => {
        const { input, target } = setup();
        target.setTarget('review', { isNew: true });
        flushSync();
        input.collectionId = 'c2';
        flushSync();
        expect(target.typedSource).toBeNull();
        expect(target.targetSource).toBeNull();
    });

    it('stops treating a typed source as new once it is listed', () => {
        const { input, target } = setup();
        target.setTarget('review', { isNew: true });
        flushSync();
        input.names = ['labels', 'predictions', 'review'];
        flushSync();
        expect(target.typedSource).toBeNull();
        expect(target.targetSource).toBe('review');

        // The source is deleted while another collection is open.
        input.collectionId = 'c2';
        flushSync();
        input.collectionId = 'c1';
        input.names = ['labels', 'predictions'];
        flushSync();
        expect(target.needsPick).toBe(true);
    });
});
