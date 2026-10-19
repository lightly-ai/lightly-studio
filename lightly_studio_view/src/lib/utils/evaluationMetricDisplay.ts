const countMetricLabels: Record<string, string | undefined> = {
    tp: 'Correct predictions (TP)',
    fp: 'Extra predictions (FP)',
    fn: 'Missed objects (FN)'
};

export function getEvaluationMetricLabel(metricName: string) {
    return Object.hasOwn(countMetricLabels, metricName) ? countMetricLabels[metricName] : undefined;
}
