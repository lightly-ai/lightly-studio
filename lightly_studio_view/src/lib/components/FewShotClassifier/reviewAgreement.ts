interface PredictionBatch {
    positiveSampleIds: string[];
    negativeSampleIds: string[];
}

interface ReviewAgreement {
    confirmedPredictions: number;
    reviewedSamples: number;
}

export function calculateReviewAgreement(
    predictions: PredictionBatch,
    selectedSampleIds: ReadonlySet<string>
): ReviewAgreement {
    const confirmedPositivePredictions = predictions.positiveSampleIds.filter((sampleId) =>
        selectedSampleIds.has(sampleId)
    ).length;
    const confirmedNegativePredictions = predictions.negativeSampleIds.filter(
        (sampleId) => !selectedSampleIds.has(sampleId)
    ).length;

    return {
        confirmedPredictions: confirmedPositivePredictions + confirmedNegativePredictions,
        reviewedSamples: predictions.positiveSampleIds.length + predictions.negativeSampleIds.length
    };
}

export function formatAgreement(confirmedPredictions: number, reviewedSamples: number): string {
    if (reviewedSamples === 0) return '0%';
    return `${Math.round((confirmedPredictions / reviewedSamples) * 100)}%`;
}
