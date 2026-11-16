// Keeps drawing and assisted labeling previews visible when the mask opacity is 0.
const MIN_PREVIEW_MASK_OPACITY = 0.3;

interface GetPreviewMaskOpacityParams {
    maskOpacity: number;
    // Alpha of the custom label color, which also scales the saved mask.
    labelAlpha?: number;
}

export const getPreviewMaskOpacity = ({
    maskOpacity,
    labelAlpha = 1
}: GetPreviewMaskOpacityParams): number =>
    Math.max(MIN_PREVIEW_MASK_OPACITY, labelAlpha * maskOpacity);
