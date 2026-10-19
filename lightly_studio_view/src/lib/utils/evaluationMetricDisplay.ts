const countMetrics: Record<string, { label: string; description: string } | undefined> = {
    tp: {
        label: 'Correct predictions (TP)',
        description: 'True positives: predictions matched to a reference annotation.'
    },
    fp: {
        label: 'Extra predictions (FP)',
        description: 'False positives: predictions with no matching reference annotation.'
    },
    fn: {
        label: 'Missed objects (FN)',
        description: 'False negatives: reference annotations with no matching prediction.'
    }
};

export function getEvaluationMetricDisplay(metricName: string) {
    return Object.hasOwn(countMetrics, metricName) ? countMetrics[metricName] : undefined;
}
