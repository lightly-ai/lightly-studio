import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useSetTargetSource } from './useSetTargetSource';

const mocks = vi.hoisted(() => ({
    context: {} as AnnotationLabelContext,
    updateLastAnnotationSource: vi.fn()
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ context: mocks.context })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ updateLastAnnotationSource: mocks.updateLastAnnotationSource })
}));

describe('useSetTargetSource', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.context = {};
    });

    it('remembers the trimmed pick for the collection', () => {
        useSetTargetSource(() => 'col-1')('  labels ');

        expect(mocks.updateLastAnnotationSource).toHaveBeenCalledWith('col-1', 'labels');
        expect(mocks.context.typedAnnotationSource).toBeUndefined();
    });

    it('lets a typed new name be the target before its source exists', () => {
        useSetTargetSource(() => 'col-1')('review', { isNew: true });

        expect(mocks.context.typedAnnotationSource).toBe('review');
    });

    it('ignores a blank name and a hidden source', () => {
        mocks.context.hiddenAnnotationSources = ['labels'];

        useSetTargetSource(() => 'col-1')('  ');
        useSetTargetSource(() => 'col-1')('labels');

        expect(mocks.updateLastAnnotationSource).not.toHaveBeenCalled();
    });
});
