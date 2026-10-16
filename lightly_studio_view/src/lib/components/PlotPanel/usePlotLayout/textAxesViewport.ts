import type { ViewportState } from 'embedding-atlas/svelte';
import type { ProjectionAxes } from '$lib/api/lightly_studio_local';

// Half the visible range of each text axis, in difference of cosine similarity. Real axes on a
// celebrity dataset reach about ±0.15 and nonsense texts about ±0.05. A fixed range, the same on
// both axes, shows how strongly the images vary along each axis, which fitting to the data hides.
export const TEXT_AXES_HALF_RANGE = 0.2;

interface GetDefaultViewportParams {
    plotAxes: ProjectionAxes | null;
    // The plot size in pixels.
    width: number;
    height: number;
}

// The viewport to start from: fixed and centered on the origin for text axes, null (fit to the
// data) for PaCMAP. Embedding Atlas maps the scale to [-1, 1] along the longer side of the plot,
// so the shorter side shows less of the data.
export const getDefaultViewport = ({
    plotAxes,
    width,
    height
}: GetDefaultViewportParams): ViewportState | null => {
    if (!plotAxes) return null;
    const scale = Math.min(width, height) / (Math.max(width, height) * TEXT_AXES_HALF_RANGE);
    return { x: 0, y: 0, scale };
};
