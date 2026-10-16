interface IsPanEnabledParams {
    isEditingMode: boolean;
    isDrawing?: boolean;
    isErasing?: boolean;
    status: string;
    isDrawingInstancesBox: boolean;
}

// Assisted labeling tools only block panning in edit mode, since the status outlives it.
export const isPanEnabled = ({
    isEditingMode,
    isDrawing,
    isErasing,
    status,
    isDrawingInstancesBox
}: IsPanEnabledParams): boolean => {
    const isAssistedToolBlocking =
        status === 'smart-select' || (status === 'find-instances' && isDrawingInstancesBox);
    return !(isDrawing || isErasing || (isEditingMode && isAssistedToolBlocking));
};
