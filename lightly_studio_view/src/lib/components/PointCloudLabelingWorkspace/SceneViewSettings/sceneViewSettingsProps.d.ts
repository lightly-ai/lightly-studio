/** Inputs and callbacks for scene view settings. */
export interface SceneViewSettingsProps {
    /** Whether Top, Side, and Front views are visible. */
    showOrthographicViews: boolean;
    /** Screen-space point size in CSS pixels. */
    pointSize: number;
    /** Whether navigation buttons and shortcut hints are shown. */
    showNavigationHelpers: boolean;
    /** Whether hovered annotation metadata is shown in scene viewports. */
    showAnnotationTooltips: boolean;
    /** Disables unavailable settings while preferences are loading. */
    disabled?: boolean;
    /** Updates orthographic projection visibility. */
    onToggle: (showOrthographicViews: boolean) => void;
    /** Updates the preferred point size. */
    onPointSizeChange: (pointSize: number) => void;
    /** Updates navigation helper visibility. */
    onToggleNavigationHelpers: (show: boolean) => void;
    /** Updates annotation tooltip visibility for all scene viewports. */
    onToggleAnnotationTooltips: (show: boolean) => void;
}
