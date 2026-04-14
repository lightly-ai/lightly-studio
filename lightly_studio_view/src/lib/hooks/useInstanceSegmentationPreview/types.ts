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

export interface UseInstanceSegmentationPreviewParams {
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
}

export interface DrawBrushLineParams {
    from: BrushPoint;
    to: BrushPoint;
    brushRadius: number;
    width: number;
    height: number;
}

export type EnsureSourceMaskContext = (
    width: number,
    height: number
) => CanvasRenderingContext2D | null;
