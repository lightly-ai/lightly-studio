import type { InstancesAnnotationRequest } from '$lib/api/lightly_studio_local';
import { InstancesAnnotationRequestSchema } from '$lib/api/lightly_studio_local/schemas.gen';
import type { boxFromPoints } from '$lib/components/SampleDetails/useDragBox/useDragBox.helpers';

export const MAX_INSTANCES_LIMIT =
    InstancesAnnotationRequestSchema.properties.max_instances.maximum;

interface BuildInstancesRequestBodyParams {
    collectionId: string;
    sampleId: string;
    prompt: string;
    boxes: ReturnType<typeof boxFromPoints>[];
    maxInstances: number;
}

type CanGenerateInstancesParams = Pick<BuildInstancesRequestBodyParams, 'prompt'>;

// Boxes alone find only the boxed objects, so the endpoint needs a text prompt.
export const canGenerateInstances = ({ prompt }: CanGenerateInstancesParams): boolean =>
    prompt.trim().length > 0;

export const buildInstancesRequestBody = ({
    collectionId,
    sampleId,
    prompt,
    boxes,
    maxInstances
}: BuildInstancesRequestBodyParams): InstancesAnnotationRequest => ({
    collection_id: collectionId,
    sample_id: sampleId,
    text_prompt: prompt.trim(),
    boxes: boxes.length > 0 ? boxes : null,
    max_instances: maxInstances
});
