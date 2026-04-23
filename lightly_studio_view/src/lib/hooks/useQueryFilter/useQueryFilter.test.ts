import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { useQueryFilter, QUERY_FILTER_FEATURE_FLAG } from './useQueryFilter';
import * as featureFlagsModule from '$lib/hooks/useFeatureFlags/useFeatureFlags';

describe('useQueryFilter', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    function mockFeatureFlags(flags: string[]) {
        const store = writable(flags);
        vi.spyOn(featureFlagsModule, 'useFeatureFlags').mockReturnValue({
            featureFlags: store,
            error: writable(null)
        });
    }

    it('has isEnabled set to true when the feature flag is present', () => {
        mockFeatureFlags([QUERY_FILTER_FEATURE_FLAG]);

        const { isEnabled } = useQueryFilter();

        expect(get(isEnabled)).toBe(true);
    });

    it('has isEnabled set to false when the feature flag is absent', () => {
        mockFeatureFlags([]);

        const { isEnabled } = useQueryFilter();

        expect(get(isEnabled)).toBe(false);
    });

    it('toggles editing state when enabled', () => {
        mockFeatureFlags([QUERY_FILTER_FEATURE_FLAG]);

        const { isEditing, toggleEditing } = useQueryFilter();
        const initial = get(isEditing);

        toggleEditing();
        expect(get(isEditing)).toBe(!initial);

        toggleEditing();
        expect(get(isEditing)).toBe(initial);
    });

    it('ignores toggle when the feature flag is disabled', () => {
        mockFeatureFlags([]);

        const { isEditing, toggleEditing } = useQueryFilter();
        const initial = get(isEditing);

        toggleEditing();
        expect(get(isEditing)).toBe(initial);
    });
});
