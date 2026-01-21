import { readImageOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useImage = ({
	sampleId
}: {
	sampleId: string;
}): { image: CreateQueryResult<ImageView, Error>; refetch: () => void } => {
    const readImage = readImageOptions({
        path: {
            sample_id: sampleId
        }
    });
    const client = useQueryClient();
    const image = createQuery(readImage);
    const refetch = () => {
        client.invalidateQueries({ queryKey: readImage.queryKey });
    };

    return {
        refetch,
        image
    };
};
