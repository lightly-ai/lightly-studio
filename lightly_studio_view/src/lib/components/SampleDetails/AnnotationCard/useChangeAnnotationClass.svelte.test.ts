import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import { useChangeAnnotationClass } from './useChangeAnnotationClass.svelte';

const mocks = vi.hoisted(() => ({
    updateAnnotations: vi.fn(),
    pickClass: vi.fn(),
    setAnnotationLabel: vi.fn(),
    refetchAnnotation: vi.fn(),
    error: vi.fn(),
    undoActions: [] as ReversibleAction[]
}));
vi.mock('$lib/hooks', () => ({
    useAnnotation: () => ({ refetch: mocks.refetchAnnotation }),
    useGlobalStorage: () => ({
        addReversibleAction: (action: ReversibleAction) => mocks.undoActions.push(action)
    }),
    useStickyClass: () => ({ pickClass: mocks.pickClass }),
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: mocks.updateAnnotations })
}));
vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ setAnnotationLabel: mocks.setAnnotationLabel })
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: mocks.error } }));

const box: AnnotationView = {
    sample_id: 'box',
    parent_sample_id: 'image',
    annotation_collection_id: 'predictions',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'car' },
    created_at: new Date()
};

// The `annotation` prop keeps the class from before the request, which the queries refresh one
// round trip later. Every test therefore picks twice against the same prop.
const setup = () =>
    useChangeAnnotationClass(() => ({
        collectionId: 'images',
        annotation: box,
        refetch: vi.fn()
    })).changeClass;

describe('useChangeAnnotationClass', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.undoActions = [];
        mocks.updateAnnotations.mockResolvedValue(undefined);
    });

    it('changes the class of the annotation', async () => {
        await setup()('truck');

        expect(mocks.updateAnnotations).toHaveBeenCalledExactlyOnceWith([
            { annotation_id: 'box', collection_id: 'images', label_name: 'truck' }
        ]);
        expect(mocks.pickClass).toHaveBeenCalledWith('images', 'truck');
    });

    it('changes back to the class of before while the prop is stale', async () => {
        const changeClass = setup();
        await changeClass('truck');
        mocks.updateAnnotations.mockClear();

        await changeClass('car');

        expect(mocks.updateAnnotations).toHaveBeenCalledExactlyOnceWith([
            { annotation_id: 'box', collection_id: 'images', label_name: 'car' }
        ]);
    });

    it('undoes a second change to the class the first one set', async () => {
        const changeClass = setup();
        await changeClass('truck');
        await changeClass('bus');
        mocks.updateAnnotations.mockClear();

        await mocks.undoActions[mocks.undoActions.length - 1].execute();

        expect(mocks.updateAnnotations).toHaveBeenCalledExactlyOnceWith([
            { annotation_id: 'box', collection_id: 'images', label_name: 'truck' }
        ]);
    });

    it('ignores a pick of the class the annotation has', async () => {
        await setup()('car');

        expect(mocks.updateAnnotations).not.toHaveBeenCalled();
    });
});
