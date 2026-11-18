export function togglePickedSampleId(pickedSampleIds: string[], sampleId: string): string[] {
    if (pickedSampleIds.includes(sampleId)) {
        return pickedSampleIds.filter((pickedId) => pickedId !== sampleId);
    }
    return [...pickedSampleIds, sampleId];
}
