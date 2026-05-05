export interface BrushPoint {
    x: number;
    y: number;
}

export interface ParsedColor {
    r: number;
    g: number;
    b: number;
    a: number;
}

export interface UseSegmentationMaskPreviewParams {
    onPreviewVisibilityChange?: (visible: boolean) => void;
}

export interface SchedulePreviewComposeParams {
    width: number;
    height: number;
    color: ParsedColor;
    isDrawing: boolean;
}

export interface DrawBrushDotParams {
    point: BrushPoint;
    brushRadius: number;
    width: number;
    height: number;
    compositeOperation?: GlobalCompositeOperation;
}

export interface DrawBrushLineParams {
    from: BrushPoint;
    to: BrushPoint;
    brushRadius: number;
    width: number;
    height: number;
    compositeOperation?: GlobalCompositeOperation;
}

export type EnsureSourceMaskContext = (
    width: number,
    height: number
) => CanvasRenderingContext2D | null;
