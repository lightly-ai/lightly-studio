interface IsPanEnabledParams {
    isDrawing?: boolean;
    isErasing?: boolean;
    // Set by an assisted labeling tool that uses drags on the image.
    blocksPan: boolean;
}

export const isPanEnabled = ({ isDrawing, isErasing, blocksPan }: IsPanEnabledParams): boolean =>
    !(isDrawing || isErasing || blocksPan);

interface GetDrawerLabelParams {
    isAnnotationSelected: boolean;
    contextLabel: string | null | undefined;
    stickyClass: string | undefined;
}

/**
 * The class whose color the drawing tools use. A selected annotation keeps its class. Otherwise
 * the next annotation gets the sticky class, so the stroke shows that one.
 */
export const getDrawerLabel = ({
    isAnnotationSelected,
    contextLabel,
    stickyClass
}: GetDrawerLabelParams): string | null =>
    (isAnnotationSelected ? contextLabel : stickyClass) ?? null;
