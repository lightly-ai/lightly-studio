import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useCreateLabel } from '$lib/hooks';
import { useQueryClient } from '@tanstack/svelte-query';

// Gives the class id of each class name and creates the classes that are missing.
export const useLabelIds = ({
    getCollectionId,
    getDatasetId
}: {
    getCollectionId: () => string;
    getDatasetId: () => string;
}) => {
    const { createLabel } = useCreateLabel({ getCollectionId });
    const client = useQueryClient();
    const getQueryOptions = () =>
        readAnnotationLabelsOptions({ path: { collection_id: getCollectionId() } });

    // Fetches the classes from the server, so classes created by an earlier call are included.
    const fetchLabelIds = async () => {
        const labels = await client.fetchQuery(getQueryOptions());
        return new Map(
            labels.map((label): [string, string] => [
                label.annotation_label_name,
                label.annotation_label_id!
            ])
        );
    };

    const getLabelIds = async (classNames: string[]) => {
        const labelIds = await fetchLabelIds();
        const newClassNames = [...new Set(classNames)].filter((name) => !labelIds.has(name));
        try {
            for (const className of newClassNames) {
                const label = await createLabel({
                    dataset_id: getDatasetId(),
                    annotation_label_name: className
                });
                labelIds.set(className, label.annotation_label_id!);
            }
        } finally {
            // Also after a failure, so the classes created before it show up.
            if (newClassNames.length > 0) {
                client.invalidateQueries({ queryKey: getQueryOptions().queryKey });
            }
        }
        return labelIds;
    };

    return { getLabelIds };
};
