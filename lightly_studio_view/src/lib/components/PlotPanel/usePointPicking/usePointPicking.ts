import { writable } from 'svelte/store';
import type { DataPoint } from 'embedding-atlas/svelte';
import { togglePickedSampleId } from '../pickedSamples/pickedSamples';

// The library starts a rectangle when a shift-press moves more than 2px. A shift-press that
// moves less than this is still a click, because a hand moves a little during a click.
const MAX_SHIFT_CLICK_DISTANCE_PX = 6;

interface UsePointPickingParams {
    getPickedSampleIds: () => string[];
    getHoveredSampleId: () => string | null;
    commitPickedSampleIds: (sampleIds: string[]) => void;
}

interface ShiftPress {
    clientX: number;
    clientY: number;
    hoveredSampleId: string | null;
}

/**
 * Picks single points in the embedding plot with Shift + click. A click on a picked point
 * removes it.
 */
export function usePointPicking(params: UsePointPickingParams) {
    const { getPickedSampleIds, getHoveredSampleId, commitPickedSampleIds } = params;
    // The library's selection callback does not give the click modifiers, so the shift state
    // comes from the pointer down.
    let shiftPress: ShiftPress | null = null;
    // The library keeps its own point selection. A reset after each click makes the library
    // report only the clicked point and draw no selection of its own.
    const librarySelection = writable<DataPoint[]>([]);

    const togglePick = (sampleId: string) => {
        commitPickedSampleIds(togglePickedSampleId(getPickedSampleIds(), sampleId));
    };

    const onPointerDown = (event: PointerEvent) => {
        shiftPress = event.shiftKey
            ? {
                  clientX: event.clientX,
                  clientY: event.clientY,
                  hoveredSampleId: getHoveredSampleId()
              }
            : null;
    };

    const onSelection = (points: DataPoint[] | null) => {
        librarySelection.set([]);
        const clickedSampleId = points?.[0]?.identifier;
        if (shiftPress === null || typeof clickedSampleId !== 'string') return;
        togglePick(clickedSampleId);
    };

    const isShortShiftDrag = (event: MouseEvent) => {
        if (shiftPress === null) return false;
        const distance = Math.hypot(
            event.clientX - shiftPress.clientX,
            event.clientY - shiftPress.clientY
        );
        return distance < MAX_SHIFT_CLICK_DISTANCE_PX;
    };

    const pickPressedPoint = () => {
        const sampleId = shiftPress?.hoveredSampleId;
        if (sampleId) togglePick(sampleId);
    };

    return { librarySelection, onPointerDown, onSelection, isShortShiftDrag, pickPressedPoint };
}
