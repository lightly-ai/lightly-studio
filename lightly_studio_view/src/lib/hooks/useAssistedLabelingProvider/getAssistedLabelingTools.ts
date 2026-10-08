import type { AssistedLabelingProviderView } from '$lib/api/lightly_studio_local';

const LOADING_REASON = 'Loading the AI-assisted labeling provider…';
const ERROR_REASON = 'Could not load the AI-assisted labeling provider.';
const DEFAULT_MAX_INSTANCES = 16;

// Turns the active provider into the state of the smart select and find all instances
// tools. A disabled reason of null means the tool is usable.
export const getAssistedLabelingTools = ({
    provider,
    isError
}: {
    provider: AssistedLabelingProviderView | undefined;
    isError: boolean;
}) => {
    const capabilities = provider?.capabilities;
    const providerReason = getProviderReason(provider, isError);
    const unsupported = (feature: string) =>
        `${provider?.display_name ?? 'The provider'} does not support ${feature}.`;

    const canSmartSelect = Boolean(capabilities?.positive_points || capabilities?.boxes);
    const maxInstances = Math.max(1, capabilities?.max_instances ?? 1);

    return {
        smartSelectDisabledReason:
            providerReason ?? (canSmartSelect ? null : unsupported('smart select')),
        instancesDisabledReason:
            providerReason ?? (capabilities?.text_prompt ? null : unsupported('text prompts')),
        positivePoints: Boolean(capabilities?.positive_points),
        negativePoints: Boolean(capabilities?.negative_points),
        boxes: Boolean(capabilities?.boxes),
        maxInstances,
        defaultMaxInstances: Math.min(DEFAULT_MAX_INSTANCES, maxInstances)
    };
};

const getProviderReason = (
    provider: AssistedLabelingProviderView | undefined,
    isError: boolean
): string | null => {
    if (isError) return ERROR_REASON;
    if (!provider) return LOADING_REASON;
    return provider.unavailable_reason;
};
