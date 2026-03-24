import { getAdjacentSamplesOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient, type QueryClient } from '@tanstack/svelte-query';

import type {
    AnnotationsFilter,
    ImageFilter,
    SampleType,
    VideoFilter,
    VideoFrameAdjacentFilter
} from '$lib/api/lightly_studio_local/types.gen';

export type AdjacentSamplesRequestBody =
    | {
          sample_type: Extract<SampleType, 'image'>;
          collection_id: string;
          filters?: ({ filter_type: 'image' } & ImageFilter) | null;
          text_embedding?: number[];
      }
    | {
          sample_type: Extract<SampleType, 'video'>;
          collection_id: string;
          filters?: ({ filter_type: 'video' } & VideoFilter) | null;
          text_embedding?: number[];
      }
    | {
          sample_type: Extract<SampleType, 'video_frame'>;
          collection_id: string;
          filters?: ({ filter_type: 'video_frame_adjacent' } & VideoFrameAdjacentFilter) | null;
      }
    | {
          sample_type: Extract<SampleType, 'annotation'>;
          collection_id: string;
          filters?: ({ filter_type: 'annotations' } & AnnotationsFilter) | null;
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
