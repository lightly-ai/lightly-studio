interface IsPanEnabledParams {
    isEditingMode: boolean;
    isDrawing?: boolean;
    isErasing?: boolean;
    status: string;
}

// Assisted labeling tools only block panning in edit mode, since the status outlives it.
export const isPanEnabled = ({
    isEditingMode,
    isDrawing,
    isErasing,
    status
}: IsPanEnabledParams): boolean =>
    !(isDrawing || isErasing || (isEditingMode && status === 'smart-select'));
