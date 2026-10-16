import { prepareAnnotationImage } from '$lib/api/lightly_studio_local';

// Sample IDs that were prepared or are being prepared, shared across tool activations.
const preparedSampleIds = new Set<string>();

// Lets the provider upload the image before the first smart select or instances request.
// Fires once per sample. A failure is only logged, since the preview requests prepare the
// image on their own if needed.
export const usePrepareAnnotationImage = () => {
    const prepareImage = ({
        collectionId,
        sampleId
    }: {
        collectionId: string;
        sampleId: string;
    }) => {
        if (preparedSampleIds.has(sampleId)) return;
        preparedSampleIds.add(sampleId);
        prepareAnnotationImage({
            body: { collection_id: collectionId, sample_id: sampleId },
            throwOnError: true
        }).catch((error: unknown) => {
            preparedSampleIds.delete(sampleId);
            console.warn('Could not prepare the image for AI-assisted labeling:', error);
        });
    };

    return { prepareImage };
};
