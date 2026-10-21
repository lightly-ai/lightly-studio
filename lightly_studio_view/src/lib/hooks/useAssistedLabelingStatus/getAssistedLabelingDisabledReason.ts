import type { AssistedLabelingStatusView } from '$lib/api/lightly_studio_local';

// Returns why the assisted labeling tools are disabled, or null if they are usable.
export const getAssistedLabelingDisabledReason = ({
    status,
    isError
}: {
    status: AssistedLabelingStatusView | undefined;
    isError: boolean;
}): string | null => {
    if (status) return status.unavailable_reason;
    if (isError) return 'Could not load the assisted labeling status.';
    return 'Loading the assisted labeling status…';
};
