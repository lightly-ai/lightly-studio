import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { describe, it, expect, vi } from 'vitest';
import ProviderHarness from './PointCloudWorkspaceProviderHarness.svelte';
import NoProviderHarness from './UsePointCloudWorkspaceContextNoProviderHarness.svelte';
import type { PointCloudWorkspaceContext } from './types';

// The provider harness builds the context, which calls useMcapSequenceSummary; stub it out.
vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({
        summary: { data: undefined, isLoading: false, isError: false },
        refetch: vi.fn()
    })
}));

describe('usePointCloudWorkspaceContext', () => {
    it('returns the context registered by the provider', () => {
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
        expect(result?.used).toBe(result?.created);
    });

    it('throws when no provider is present', () => {
        expect(() => render(NoProviderHarness)).toThrow('PointCloudWorkspaceContext not found');
    });
});
