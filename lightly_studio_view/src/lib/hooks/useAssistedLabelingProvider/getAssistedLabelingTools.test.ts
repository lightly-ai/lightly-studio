import { describe, expect, it } from 'vitest';
import type { AssistedLabelingProviderView } from '$lib/api/lightly_studio_local';
import { getAssistedLabelingTools } from './getAssistedLabelingTools';

const provider: AssistedLabelingProviderView = {
    provider_id: 'fake',
    display_name: 'Fake',
    sends_data_to_third_party: false,
    capabilities: {
        positive_points: true,
        negative_points: true,
        boxes: true,
        text_prompt: true,
        max_instances: 32
    },
    unavailable_reason: null
};

describe('getAssistedLabelingTools', () => {
    it('enables both tools for a provider with all capabilities', () => {
        expect(getAssistedLabelingTools({ provider, isError: false })).toEqual({
            smartSelectDisabledReason: null,
            instancesDisabledReason: null,
            positivePoints: true,
            negativePoints: true,
            boxes: true,
            maxInstances: 32,
            defaultMaxInstances: 16
        });
    });

    it('disables both tools with the unavailable reason', () => {
        const tools = getAssistedLabelingTools({
            provider: { ...provider, unavailable_reason: 'FAL_KEY is not set.' },
            isError: false
        });
        expect(tools.smartSelectDisabledReason).toBe('FAL_KEY is not set.');
        expect(tools.instancesDisabledReason).toBe('FAL_KEY is not set.');
    });

    it('disables both tools while loading or after a failed request', () => {
        expect(
            getAssistedLabelingTools({ provider: undefined, isError: false })
                .smartSelectDisabledReason
        ).toMatch(/Loading/);
        expect(
            getAssistedLabelingTools({ provider: undefined, isError: true }).instancesDisabledReason
        ).toMatch(/Could not load/);
    });

    it('gates features on the provider capabilities', () => {
        const tools = getAssistedLabelingTools({
            provider: {
                ...provider,
                capabilities: {
                    positive_points: true,
                    negative_points: false,
                    boxes: false,
                    text_prompt: false,
                    max_instances: 4
                }
            },
            isError: false
        });
        expect(tools.smartSelectDisabledReason).toBeNull();
        expect(tools.instancesDisabledReason).toBe('Fake does not support text prompts.');
        expect(tools.negativePoints).toBe(false);
        expect(tools.boxes).toBe(false);
        expect(tools.maxInstances).toBe(4);
        expect(tools.defaultMaxInstances).toBe(4);
    });

    it('disables smart select without point or box support', () => {
        const tools = getAssistedLabelingTools({
            provider: {
                ...provider,
                capabilities: { ...provider.capabilities, positive_points: false, boxes: false }
            },
            isError: false
        });
        expect(tools.smartSelectDisabledReason).toBe('Fake does not support smart select.');
    });
});
