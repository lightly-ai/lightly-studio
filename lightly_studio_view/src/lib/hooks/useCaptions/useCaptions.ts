import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';

export const useCaptions = () => {
    const { createCaption } = useCreateCaption();
    const { deleteCaption } = useDeleteCaption();

    return {
        createCaption,
        deleteCaption
    };
};
