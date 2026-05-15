import {
    createCaption as createCaptionRequest,
    type CaptionCreateInput,
    type CreateCaptionResponse
} from '$lib/api/lightly_studio_local';

export const useCreateCaption = () => {
    const createCaption = async (inputs: CaptionCreateInput): Promise<CreateCaptionResponse> => {
        const { data } = await createCaptionRequest({
            body: inputs,
            throwOnError: true
        });
        return data;
    };

    return {
        createCaption
    };
};
