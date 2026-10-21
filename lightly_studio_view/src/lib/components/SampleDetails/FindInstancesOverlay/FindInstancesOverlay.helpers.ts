import type { InstancesAnnotationRequest } from '$lib/api/lightly_studio_local';
import type { boxFromPoints } from '$lib/components/SampleDetails/useDragBox/useDragBox.helpers';

// Boxes alone find only the boxed objects, so the endpoint needs a text prompt.
export const canGenerateInstances = ({ prompt }: { prompt: string }): boolean =>
    prompt.trim().length > 0;

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
    boxes: ReturnType<typeof boxFromPoints>[];
    maxInstances: number;
}): InstancesAnnotationRequest => ({
    collection_id: collectionId,
    sample_id: sampleId,
    text_prompt: prompt.trim(),
    boxes: boxes.length > 0 ? boxes : null,
    max_instances: maxInstances
});
