import type { ToolbarStatus } from '$lib/contexts/SampleDetailsToolbar.svelte';

interface IsPanEnabledParams {
    isDrawing?: boolean;
    isErasing?: boolean;
    status: ToolbarStatus;
    isDrawingInstancesBox: boolean;
}

export const isPanEnabled = ({
    isDrawing,
    isErasing,
    status,
    isDrawingInstancesBox
}: IsPanEnabledParams): boolean =>
    !(
        isDrawing ||
        isErasing ||
        status === 'smart-select' ||
        (status === 'find-instances' && isDrawingInstancesBox)
    );
