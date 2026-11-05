import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { setAnnotationLabelColorMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getAnnotationClassId, useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';

type CustomColor = NonNullable<
    ReturnType<ReturnType<typeof useCustomLabelColors>['getCustomColor']>
>;

interface UseSaveAnnotationClassColorReturn {
    saveClassColor: (name: string, color: CustomColor) => Promise<void>;
}

const ERROR_MESSAGE = 'Could not save the annotation class color.';
const CLASS_LIST_QUERY_IDS = ['readAnnotationLabels', 'readAnnotationLabelsWithCounts'];

// The last save of each class ID, so saves of one class run one at a time.
const pendingSaves = new Map<string, Promise<unknown>>();

// Saves the color of an annotation class in the dataset. Rejects when the save fails.
export const useSaveAnnotationClassColor = (): UseSaveAnnotationClassColorReturn => {
    const client = useQueryClient();
    const mutation = createMutation(() => ({
        ...setAnnotationLabelColorMutation(),
        onError: () => toast.error(ERROR_MESSAGE),
        onSettled: () =>
            client.invalidateQueries({
                predicate: (q) =>
                    CLASS_LIST_QUERY_IDS.includes((q.queryKey[0] as { _id?: string })?._id ?? '')
            })
    }));

    const saveClassColor = async (name: string, color: CustomColor) => {
        const labelId = getAnnotationClassId(name);
        if (!labelId) {
            toast.error(ERROR_MESSAGE);
            throw new Error(`Unknown annotation class: ${name}`);
        }
        const previous = pendingSaves.get(labelId) ?? Promise.resolve();
        const save = previous
            .catch(() => undefined)
            .then(() =>
                mutation.mutateAsync({
                    path: { label_id: labelId },
                    body: { color: color.color, alpha: color.alpha }
                })
            );
        pendingSaves.set(labelId, save);
        await save;
    };

    return { saveClassColor };
};
