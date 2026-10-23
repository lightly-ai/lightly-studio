import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { getAssistedLabelingStatusOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { AssistedLabelingStatusView } from '$lib/api/lightly_studio_local';
import { useAssistedLabelingStatus } from './useAssistedLabelingStatus.svelte';

describe('useAssistedLabelingStatus', () => {
    const queryResult = {
        data: { unavailable_reason: 'Set the FAL_KEY environment variable.' },
        isError: false
    } as unknown as CreateQueryResult<AssistedLabelingStatusView, Error>;

    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('queries the status and returns its disabled reason', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(queryResult);

        const status = useAssistedLabelingStatus();

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.queryKey).toEqual(getAssistedLabelingStatusOptions().queryKey);
        expect(status.disabledReason).toBe('Set the FAL_KEY environment variable.');
    });
});
