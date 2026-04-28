import type {
    AnnotationCollectionView,
    EvaluationMetrics,
    EvaluationResultView,
    TagView
} from '$lib/api/lightly_studio_local';

export const metricRows: Array<{ key: keyof EvaluationMetrics; label: string }> = [
    { key: 'precision', label: 'Precision' },
    { key: 'recall', label: 'Recall' },
    { key: 'f1', label: 'F1-Score' },
    { key: 'mAP', label: 'mAP' },
    { key: 'avg_confidence', label: 'Avg Confidence' }
];

export const getGroundTruthCollections = (collections: AnnotationCollectionView[] | undefined) =>
    (collections ?? []).filter((collection) => collection.is_ground_truth);

export const getPredictionCollections = (collections: AnnotationCollectionView[] | undefined) =>
    (collections ?? []).filter((collection) => !collection.is_ground_truth);

export const getAvailableSubsetNames = (result: EvaluationResultView | undefined): string[] => {
    if (!result) {
        return [];
    }

    const subsetNames = new Set<string>(['all']);

    for (const subsets of Object.values(result.metrics)) {
        for (const subsetName of Object.keys(subsets)) {
            subsetNames.add(subsetName);
        }
    }

    return Array.from(subsetNames);
};

export const getSelectedSubsetNames = ({
    result,
    tags,
    selectedTagIds
}: {
    result: EvaluationResultView | undefined;
    tags: TagView[];
    selectedTagIds: string[];
}) => {
    const availableSubsetNames = getAvailableSubsetNames(result);
    const selectedTagNames = selectedTagIds
        .map((tagId) => tags.find((tag) => tag.tag_id === tagId)?.name)
        .filter((name): name is string => Boolean(name));

    const requestedSubsetNames =
        selectedTagNames.length > 0 ? ['all', ...selectedTagNames] : availableSubsetNames;

    return requestedSubsetNames.filter((subsetName, index) => {
        return availableSubsetNames.includes(subsetName) && requestedSubsetNames.indexOf(subsetName) === index;
    });
};

export const getMetricValue = (
    result: EvaluationResultView | undefined,
    modelName: string,
    subsetName: string,
    metricKey: keyof EvaluationMetrics
) => result?.metrics[modelName]?.[subsetName]?.[metricKey] ?? 0;

export const formatMetricValue = (value: number) => `${(value * 100).toFixed(1)}%`;

export const formatMetricDelta = (firstValue: number, lastValue: number) => {
    if (firstValue === lastValue) {
        return '0.0%';
    }

    const delta = lastValue - firstValue;
    return `${delta > 0 ? '+' : ''}${(delta * 100).toFixed(1)}%`;
};

export const formatEvaluationLabel = (result: EvaluationResultView) => {
    const modelCount = Object.keys(result.metrics).length;
    const createdAt = new Date(result.created_at).toLocaleString();
    return `${createdAt} · ${modelCount} model${modelCount === 1 ? '' : 's'}`;
};
