import type { ClassSetSelection } from '$lib/components/ClassSetConfig';
import type { ClassSortOption } from '../topNMatrix';

/** How the visible class set is chosen (Voxel51-style configure dialog). */
export type ClassSetConfig = ClassSetSelection<ClassSortOption>;

/** Coloring options configured in the same dialog. */
export interface ColorConfig {
    /** Multiplier applied to the color scale; higher values saturate cells faster. */
    intensity: number;
    /** When true, map counts through a logarithmic scale so small counts stay visible next to large ones. */
    logScale: boolean;
}
