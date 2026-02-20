import { getAdjacentSamplesOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient, type QueryClient } from '@tanstack/svelte-query';

import type {
    AnnotationsFilter,
    ImageFilter,
    SampleType,
    VideoFilter,
    VideoFrameFilter
} from '$lib/api/lightly_studio_local/types.gen';

export type AdjacentSamplesRequestBody =
    | {
          sample_type: Extract<SampleType, 'image'>;
          filters: ImageFilter;
          text_embedding?: number[];
      }
    | {
          sample_type: Extract<SampleType, 'video'>;
          filters: VideoFilter;
          text_embedding?: number[];
      }
    | {
          sample_type: Extract<SampleType, 'video_frame'>;
          filters: VideoFrameFilter;
          text_embedding?: number[];
      }
    | {
          sample_type: Extract<SampleType, 'annotation'>;
          filters: AnnotationsFilter;
          text_embedding?: number[];
      };

type AdjacentSamplesParams = {
    sampleId: string;
    body: AdjacentSamplesRequestBody;
};

export const useAdjacentSamples = ({
    params,
    queryClient
}: {
    params: AdjacentSamplesParams;
    queryClient?: QueryClient;
}) => {
    const options = getAdjacentSamplesOptions({
        path: {
            sample_id: params.sampleId
        },
        body: params.body
    });

    const client = useQueryClient(queryClient);
    const query = createQuery(options, client);

    const refetch = () => {
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return { query, refetch };
};
