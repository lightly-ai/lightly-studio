import {
    type AnnotationLabelCreate,
    type CreateAnnotationLabelResponse
} from '$lib/api/lightly_studio_local';
import { createAnnotationLabelMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useCanCreateAnnotationClass } from '$lib/hooks/useCanCreateAnnotationClass/useCanCreateAnnotationClass';
import { createMutation } from '@tanstack/svelte-query';

/** Rejected when the class is missing and the user may not create it. */
export class AnnotationClassNotAvailableError extends Error {
    constructor(className: string) {
        super(`Class "${className}" is no longer available. Choose another class.`);
        this.name = 'AnnotationClassNotAvailableError';
    }
}

/** Gives the text to show when `createLabel` fails. */
export const getCreateLabelErrorMessage = (error: unknown, fallback: string): string =>
    error instanceof AnnotationClassNotAvailableError ? error.message : fallback;

export const useCreateLabel = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => createAnnotationLabelMutation());
    const canCreateLabel = useCanCreateAnnotationClass();

    // Below editor it sends no request and shows nothing. The caller shows the error.
    const createLabel = (inputs: AnnotationLabelCreate) =>
        new Promise<CreateAnnotationLabelResponse>((resolve, reject) => {
            if (!canCreateLabel) {
                reject(new AnnotationClassNotAvailableError(inputs.annotation_label_name));
                return;
            }
            mutation.mutate(
                {
                    path: { collection_id: getCollectionId() },
                    body: inputs
                },
                {
                    onSuccess: (data) => {
                        resolve(data);
                    },
                    onError: (error) => {
                        reject(error);
                    }
                }
            );
        });

    return {
        createLabel,
        canCreateLabel
    };
};
