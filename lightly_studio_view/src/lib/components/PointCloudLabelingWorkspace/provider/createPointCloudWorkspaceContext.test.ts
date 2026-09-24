import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { describe, it, expect, vi } from 'vitest';
import ProviderHarness from './PointCloudWorkspaceProviderHarness.svelte';
import type { PointCloudWorkspaceContext } from './types';

// Constructing the context calls useMcapSequenceSummary; stub it so no TanStack client is needed.
vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({
        summary: { data: undefined, isLoading: false, isError: false },
        refetch: vi.fn()
    })
}));
vi.mock('$lib/hooks/useTickDetails/useTickDetails', () => ({
    useTickDetails: () => ({
        tickDetails: { data: undefined, isLoading: false, isError: false, refetch: vi.fn() }
    })
}));
vi.mock('$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte', () => ({
    useCloudPointFrame: () => ({
        query: { data: undefined, isLoading: false, isError: false, refetch: vi.fn() }
    })
}));

const renderProvider = () => {
    let result:
        | { created: PointCloudWorkspaceContext; used: PointCloudWorkspaceContext }
        | undefined;
    render(ProviderHarness, {
        datasetId: 'dataset-1',
        sequenceId: 'seq-1',
        onReady: (r) => {
            result = r;
        }
    });
    flushSync();
    if (!result) throw new Error('ProviderHarness did not initialize');
    return result;
};

describe('createPointCloudWorkspaceContext', () => {
    it('returns the context built from the given inputs', () => {
        const { created } = renderProvider();
        expect(created.datasetId).toBe('dataset-1');
        expect(created.sequenceId).toBe('seq-1');
    });

    it('registers the context so descendants read the same instance', () => {
        const { created, used } = renderProvider();
        expect(used).toBe(created);
    });
});
