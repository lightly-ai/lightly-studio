import type { HistogramRange } from './types';

interface HistogramDragRangeOptions {
    /** Bin edges of the histogram being dragged over, read lazily so it tracks data changes. */
    getBinEdges: () => number[];
    /**
     * The current range handler, read lazily: it is a component prop, so
     * capturing it once would pin the value it had at mount.
     */
    getOnRangeSelect: () => ((range: HistogramRange) => void) | undefined;
}

interface HistogramDragRange {
    /** The prospective range while a drag is in progress, for previewing it. */
    readonly range: HistogramRange | undefined;
    /** Pointer pressed over the given bin index. */
    start: (binIndex: number) => void;
    /** Pointer moved to the given bin index while a drag is in progress. */
    move: (binIndex: number) => void;
    /** Pointer released: commits the range and clears the drag. */
    end: () => void;
}

/**
 * Tracks a press-and-drag across histogram bins and turns it into a value range.
 *
 * Pressing on a bin and releasing on another selects the range across them;
 * pressing and releasing on one bin selects just that bin's interval.
 */
export function createHistogramDragRange(options: HistogramDragRangeOptions): HistogramDragRange {
    let startIndex = $state<number | null>(null);
    let currentIndex = $state<number | null>(null);

    const range = $derived.by<HistogramRange | undefined>(() => {
        if (startIndex === null || currentIndex === null) return undefined;
        const binEdges = options.getBinEdges();
        const lower = Math.min(startIndex, currentIndex);
        const upper = Math.max(startIndex, currentIndex);
        return { min: binEdges[lower], max: binEdges[upper + 1] };
    });

    return {
        get range() {
            return range;
        },
        start: (binIndex) => {
            // Without a handler there is nothing to select into, so don't preview one.
            if (!options.getOnRangeSelect()) return;
            startIndex = binIndex;
            currentIndex = binIndex;
        },
        move: (binIndex) => {
            if (startIndex === null) return;
            currentIndex = binIndex;
        },
        end: () => {
            const selected = range;
            startIndex = null;
            currentIndex = null;
            if (selected) options.getOnRangeSelect()?.(selected);
        }
    };
}
