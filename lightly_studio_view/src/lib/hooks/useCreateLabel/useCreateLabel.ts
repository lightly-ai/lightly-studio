import {
    type AnnotationLabelCreate,
    type CreateAnnotationLabelResponse
} from '$lib/api/lightly_studio_local';
import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

// PROTOTYPE: annotation classes are only created in the settings. This finds an existing
// class by name instead, ignoring case and outer spaces, and fails if there is none.
export const useCreateLabel = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const client = useQueryClient();
    const { openSettingsDialog } = useSettingsDialog();

    const createLabel = async (
        inputs: AnnotationLabelCreate
    ): Promise<CreateAnnotationLabelResponse> => {
        const labels = await client.fetchQuery(
            readAnnotationLabelsOptions({ path: { collection_id: getCollectionId() } })
        );
        const name = inputs.annotation_label_name.trim().toLowerCase();
        const label = labels.find((l) => l.annotation_label_name.trim().toLowerCase() === name);
        if (label) return label;

        toast.error(`No annotation class "${inputs.annotation_label_name}".`, {
            description: 'Pick an existing annotation class, or add it in the settings.',
            action: {
                label: 'Open settings',
                onClick: () => openSettingsDialog('annotation-classes')
            }
        });
        throw new Error(`Annotation class "${inputs.annotation_label_name}" does not exist.`);
    };

    return {
        createLabel
    };
};
