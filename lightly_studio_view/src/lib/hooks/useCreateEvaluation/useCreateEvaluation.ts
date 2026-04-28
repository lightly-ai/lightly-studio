import {
    createEvaluationMutation,
    getEvaluationQueryKey,
    listEvaluationsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    CreateEvaluationResponse,
    EvaluationCreateInput
} from '$lib/api/lightly_studio_local';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { get } from 'svelte/store';

export const useCreateEvaluation = ({ datasetId }: { datasetId: string }) => {
    const mutation = createMutation(createEvaluationMutation());
    const client = useQueryClient();

    mutation.subscribe(() => undefined);

    const createEvaluation = (body: EvaluationCreateInput) =>
        new Promise<CreateEvaluationResponse>((resolve, reject) => {
            if (!datasetId) {
                reject(new Error('Dataset is not loaded yet.'));
                return;
            }

            get(mutation).mutate(
                {
                    path: { dataset_id: datasetId },
                    body
                },
                {
                    onSuccess: async (data) => {
                        await client.invalidateQueries({
                            queryKey: listEvaluationsQueryKey({
                                path: { dataset_id: datasetId }
                            })
                        });
                        await client.invalidateQueries({
                            queryKey: getEvaluationQueryKey({
                                path: {
                                    dataset_id: datasetId,
                                    evaluation_id: data.id
                                }
                            })
                        });
                        resolve(data);
                    },
                    onError: (error) => reject(error)
                }
            );
        });

    return {
        mutation,
        createEvaluation
    };
};
