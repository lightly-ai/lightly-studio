import type { Annotation } from '../services/types';

export function groupAnnotationLabels(annotations: Annotation[]) {
    const classCountMap = new Map<string, number>();

    annotations.forEach((annotation) => {
        const className = annotation.annotation_label.annotation_label_name;
        if (className) {
            classCountMap.set(className, (classCountMap.get(className) || 0) + 1);
        }
    });

    return classCountMap;
}
