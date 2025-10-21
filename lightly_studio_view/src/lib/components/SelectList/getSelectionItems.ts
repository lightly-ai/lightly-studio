import type { AnnotationLabel } from '$lib/services/types';
import type { ListItem } from './types';

export const getSelectionItems = (labels: AnnotationLabel[]): ListItem[] => {
    const result = labels
        .map((labelItem) => {
            const label = labelItem.annotation_label_name;

            return { value: label, label };
        })
        .sort((a, b) => a.label.localeCompare(b.label));
    return result;
};
