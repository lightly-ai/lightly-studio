import type { AssistedLabelingStatusView } from '$lib/api/lightly_studio_local';

interface GetAssistedLabelingDisabledReasonParams {
    status: AssistedLabelingStatusView | undefined;
    isError: boolean;
}

// Returns why the assisted labeling tools are disabled, or null if they are usable.
export const getAssistedLabelingDisabledReason = ({
    status,
    isError
}: GetAssistedLabelingDisabledReasonParams): string | null => {
    if (status) return status.unavailable_reason;
    if (isError) return 'Could not load the assisted labeling status.';
    return 'Loading the assisted labeling status…';
};
