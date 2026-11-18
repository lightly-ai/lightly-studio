import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { getLabelingModelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { LabelingModelsView } from '$lib/api/lightly_studio_local';
import { useLabelingModels } from './useLabelingModels.svelte';

describe('useLabelingModels', () => {
    const model = { id: 'ltdetrv2-s-coco', task: 'object_detection', class_names: ['cat'] };
    const queryResult = {
        data: { models: [model] },
        isError: false
    } as unknown as CreateQueryResult<LabelingModelsView, Error>;

    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('queries the models and returns them without a disabled reason', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(queryResult);

        const labelingModels = useLabelingModels();

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.queryKey).toEqual(getLabelingModelsOptions().queryKey);
        expect(labelingModels.models).toEqual([model]);
        expect(labelingModels.disabledReason).toBeNull();
    });
});
