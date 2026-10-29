import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
import { useDistributionSettings } from './useDistributionSettings';

describe('useDistributionSettings', () => {
    it('gives each collection its own settings back', () => {
        const viewSettings = {
            config: {
                mode: 'topN' as const,
                n: 20,
                sortBy: 'name' as const,
                manualClasses: [],
                orientation: 'vertical' as const,
                valueMode: 'percentage' as const
            },
            categoricalConfigs: {},
            histogramValueModes: { metadata: { hour: 'percentage' as const } },
            wasComparingTags: false
        };
        useDistributionSettings('images-a').update((settings) => ({
            ...settings,
            countMode: AnnotationCountMode.SAMPLES,
            sourceId: 'metadata',
            groupId: 'hour',
            viewSettings
        }));

        // A reopened panel reads the same settings.
        expect(get(useDistributionSettings('images-a'))).toMatchObject({
            countMode: AnnotationCountMode.SAMPLES,
            sourceId: 'metadata',
            groupId: 'hour',
            viewSettings
        });
        expect(get(useDistributionSettings('images-b'))).toEqual({
            countMode: AnnotationCountMode.OBJECTS,
            histogramBinCount: 20,
            comparisonTagIds: [],
            sourceId: undefined,
            groupId: undefined,
            viewSettings: undefined
        });
    });
});
