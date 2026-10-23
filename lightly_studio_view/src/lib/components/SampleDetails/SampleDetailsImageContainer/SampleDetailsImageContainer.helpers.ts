import {
    isAssistedLabelingStatus,
    type ToolbarStatus
} from '$lib/contexts/SampleDetailsToolbar.svelte';

interface IsPanEnabledParams {
    isDrawing?: boolean;
    isErasing?: boolean;
    status: ToolbarStatus;
}

export const isPanEnabled = ({ isDrawing, isErasing, status }: IsPanEnabledParams): boolean =>
    !(isDrawing || isErasing || isAssistedLabelingStatus(status));
