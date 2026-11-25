import { isEqual } from 'lodash-es';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';

export interface PlotLayoutKey {
    collectionId: string;
    colorBy: GetEmbeddings2dRequest['color_by'];
    axes: GetEmbeddings2dRequest['axes'];
}

// Two requests with the same layout differ only in their filters: the old points keep their
// coordinates and colors, so the plot can show them while the new points load.
export function isSamePlotLayout(a: PlotLayoutKey, b: PlotLayoutKey): boolean {
    return isEqual(a, b);
}
