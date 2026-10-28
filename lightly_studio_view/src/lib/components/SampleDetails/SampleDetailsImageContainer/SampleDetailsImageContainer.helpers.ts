interface IsPanEnabledParams {
    isDrawing?: boolean;
    isErasing?: boolean;
    // Set by an assisted labeling tool that uses drags on the image.
    blocksPan: boolean;
}

export const isPanEnabled = ({ isDrawing, isErasing, blocksPan }: IsPanEnabledParams): boolean =>
    !(isDrawing || isErasing || blocksPan);
