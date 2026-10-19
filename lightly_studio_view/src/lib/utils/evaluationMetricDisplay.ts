const countMetrics: Record<string, { label: string } | undefined> = {
    tp: {
        label: 'Correct predictions (TP)'
    },
    fp: {
        label: 'Extra predictions (FP)'
    },
    fn: {
        label: 'Missed objects (FN)'
    }
};

export function getEvaluationMetricDisplay(metricName: string) {
    return Object.hasOwn(countMetrics, metricName) ? countMetrics[metricName] : undefined;
}
