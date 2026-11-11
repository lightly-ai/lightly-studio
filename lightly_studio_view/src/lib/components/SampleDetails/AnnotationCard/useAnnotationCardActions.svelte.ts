import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationCollections, useDeleteAnnotationWithUndo } from '$lib/hooks';
import { useChangeAnnotationClass } from './useChangeAnnotationClass.svelte';
import { useMoveAnnotationByCopy } from './useMoveAnnotationByCopy.svelte';

interface Params {
    /** The collection that owns the annotation sources. */
    collectionId: string;
    annotation: AnnotationView;
    refetch: () => void;
}

/**
 * Class change, move and delete for the selected annotation, each with undo. Call during
 * component init: it reads the annotation label context.
 */
export const useAnnotationCardActions = (getParams: () => Params) => {
    const getCollectionId = () => getParams().collectionId;
    const sources = useAnnotationCollections(() => ({ collectionId: getCollectionId() }));
    const { changeClass } = useChangeAnnotationClass(getParams);
    const moves = useMoveAnnotationByCopy(getCollectionId);
    const { deleteWithUndo } = useDeleteAnnotationWithUndo(getCollectionId);
    const { setAnnotationId } = useAnnotationLabelContext();

    // One card action at a time: a move must not copy an annotation that a class change or a
    // delete is still changing.
    let isBusy = false;
    const exclusive =
        <Args extends unknown[], Result>(
            action: (...args: Args) => Promise<Result>,
            busyResult: Result
        ) =>
        async (...args: Args): Promise<Result> => {
            if (isBusy) return busyResult;
            isBusy = true;
            try {
                return await action(...args);
            } finally {
                isBusy = false;
            }
        };

    // The move copies the annotation and deletes the original, so the card follows the copy.
    const moveTo = async (sourceName: string) => {
        const { annotation, refetch } = getParams();
        const copyId = await moves.moveByCopy(annotation, sourceName, refetch);
        if (copyId === null) return false;
        setAnnotationId(copyId);
        refetch();
        return true;
    };

    const remove = async () => {
        const { annotation, refetch } = getParams();
        if (await deleteWithUndo(annotation, refetch)) setAnnotationId(null);
    };

    const close = () => setAnnotationId(null);

    return {
        sources,
        changeClass: exclusive(changeClass, undefined),
        moveTo: exclusive(moveTo, false),
        remove: exclusive(remove, undefined),
        close,
        get isMoving() {
            return moves.isMoving;
        }
    };
};
