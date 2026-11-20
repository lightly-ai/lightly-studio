import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { getLabelingModelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { LabelingModelsView } from '$lib/api/lightly_studio_local';
import { useLabelingModels } from './useLabelingModels.svelte';

describe('useLabelingModels', () => {
    const model = { id: 'ltdetrv2-s-coco', task: 'object_detection', class_names: ['cat'] };
    const queryResult = {
        data: { models: [model], has_loading_models: false }
    } as unknown as CreateQueryResult<LabelingModelsView, Error>;

    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('queries the models and returns them', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(queryResult);

        const labelingModels = useLabelingModels(() => true);

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.queryKey).toEqual(getLabelingModelsOptions().queryKey);
        expect(options.enabled).toBe(true);
        expect(labelingModels.models).toEqual([model]);
        expect(labelingModels.isAvailable).toBe(true);
    });

    it('disables the query when getEnabled returns false', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(queryResult);

        useLabelingModels(() => false);

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.enabled).toBe(false);
    });

    it('is not available without a ready model', () => {
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue({
            data: { models: [], has_loading_models: false }
        } as unknown as CreateQueryResult<LabelingModelsView, Error>);

        expect(useLabelingModels(() => true).isAvailable).toBe(false);
    });
});
