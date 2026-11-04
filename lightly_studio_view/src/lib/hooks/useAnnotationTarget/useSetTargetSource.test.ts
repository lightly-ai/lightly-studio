import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSetTargetSource } from './useSetTargetSource';

const mocks = vi.hoisted(() => ({
    setAnnotationSource: vi.fn(),
    updateLastAnnotationSource: vi.fn()
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ setAnnotationSource: mocks.setAnnotationSource })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ updateLastAnnotationSource: mocks.updateLastAnnotationSource })
}));

describe('useSetTargetSource', () => {
    beforeEach(() => vi.clearAllMocks());

    it('sets the trimmed source and remembers it for the collection', () => {
        useSetTargetSource(() => 'col-1')('  labels ');

        expect(mocks.setAnnotationSource).toHaveBeenCalledWith('labels');
        expect(mocks.updateLastAnnotationSource).toHaveBeenCalledWith('col-1', 'labels');
    });

    it('ignores a blank name', () => {
        useSetTargetSource(() => 'col-1')('  ');

        expect(mocks.setAnnotationSource).not.toHaveBeenCalled();
        expect(mocks.updateLastAnnotationSource).not.toHaveBeenCalled();
    });
});
