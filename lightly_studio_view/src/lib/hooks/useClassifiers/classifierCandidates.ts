export const CLASSIFIER_CREATION_CANDIDATE_LIMIT = 20;

export function mergeClassifierCandidates<T extends { sample_id: string }>(
    preferredSamples: T[],
    collectionSamples: T[],
    limit = CLASSIFIER_CREATION_CANDIDATE_LIMIT
): T[] {
    const candidates = new Map<string, T>();
    for (const sample of [...preferredSamples, ...collectionSamples]) {
        candidates.set(sample.sample_id, sample);
        if (candidates.size === limit) break;
    }
    return Array.from(candidates.values());
}
