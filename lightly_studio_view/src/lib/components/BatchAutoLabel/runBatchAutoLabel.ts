import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';

interface BatchProgress {
    done: number;
    annotationCount: number;
    failedCount: number;
}

interface RunBatchAutoLabelParams {
    sampleIds: string[];
    detect: (sampleId: string) => Promise<ModelAnnotationPreview[]>;
    save: (sampleId: string, previews: ModelAnnotationPreview[]) => Promise<void>;
    // Only these classes are saved, so a run does not add every class of the model.
    classNames: Set<string>;
    signal: AbortSignal;
    onProgress: (progress: BatchProgress) => void;
}

// Labels the images one at a time and saves each image's annotations as soon as it is done,
// so stopping keeps the finished images. A failed image is recorded and skipped.
export const runBatchAutoLabel = async ({
    sampleIds,
    detect,
    save,
    classNames,
    signal,
    onProgress
}: RunBatchAutoLabelParams): Promise<{
    done: number;
    annotationCount: number;
    failedSampleIds: string[];
}> => {
    let done = 0;
    let annotationCount = 0;
    const failedSampleIds: string[] = [];
    for (const sampleId of sampleIds) {
        if (signal.aborted) break;
        try {
            const previews = await detect(sampleId);
            const kept = previews.filter((preview) => classNames.has(preview.class_name));
            if (kept.length > 0) await save(sampleId, kept);
            annotationCount += kept.length;
        } catch (error) {
            console.error(`Could not auto-label sample ${sampleId}.`, error);
            failedSampleIds.push(sampleId);
        }
        done += 1;
        onProgress({ done, annotationCount, failedCount: failedSampleIds.length });
    }
    return { done, annotationCount, failedSampleIds };
};
