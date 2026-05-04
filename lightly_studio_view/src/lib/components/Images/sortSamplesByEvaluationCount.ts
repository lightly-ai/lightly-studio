import type { EvaluationSampleSort } from '$lib/hooks/useGlobalStorage';

type SampleWithId = {
    sample_id: string;
};

type SampleCounts = Record<string, Record<string, number>>;

export const sortSamplesByEvaluationCount = <TSample extends SampleWithId>(
    samples: TSample[],
    sampleCounts: SampleCounts,
    sort: EvaluationSampleSort
): TSample[] => {
    if (!sort) {
        return samples;
    }

    const directionFactor = sort.direction === 'asc' ? 1 : -1;
    const indexBySampleId = new Map(samples.map((sample, index) => [sample.sample_id, index]));

    return [...samples].sort((left, right) => {
        const leftValue = sampleCounts[left.sample_id]?.[sort.metric] ?? 0;
        const rightValue = sampleCounts[right.sample_id]?.[sort.metric] ?? 0;

        if (leftValue !== rightValue) {
            return (leftValue - rightValue) * directionFactor;
        }

        return (
            (indexBySampleId.get(left.sample_id) ?? 0) - (indexBySampleId.get(right.sample_id) ?? 0)
        );
    });
};
