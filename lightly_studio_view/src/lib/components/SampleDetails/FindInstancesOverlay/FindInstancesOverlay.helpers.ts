import type { InstancesAnnotationRequest } from '$lib/api/lightly_studio_local';
import type { NormalizedBox } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';

export const canGenerateInstances = ({
    prompt,
    boxCount
}: {
    prompt: string;
    boxCount: number;
}): boolean => prompt.trim().length > 0 || boxCount > 0;

export const buildInstancesRequestBody = ({
    collectionId,
    sampleId,
    prompt,
    boxes,
    maxInstances
}: {
    collectionId: string;
    sampleId: string;
    prompt: string;
    boxes: NormalizedBox[];
    maxInstances: number;
}): InstancesAnnotationRequest => ({
    collection_id: collectionId,
    sample_id: sampleId,
    prompt: prompt.trim() || null,
    boxes: boxes.length > 0 ? boxes : null,
    max_instances: maxInstances
});
