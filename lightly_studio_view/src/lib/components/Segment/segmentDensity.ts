import { getContext, setContext } from 'svelte';

/**
 * How tightly a `Segment` and its rows are packed.
 *
 * `comfortable` is the standalone scale used by panels and the sample details side panel.
 * `compact` is the app sidebar scale: smaller trigger type and tighter rows, so a dozen
 * filter groups fit in a 264px rail without scrolling past the fold immediately.
 */
export type SegmentDensity = 'comfortable' | 'compact';

/**
 * Classes for the parts of a checkbox row inside a `Segment`.
 *
 * Kept here rather than in each menu so the sidebar scale is defined once. Menus read it from
 * the density context, which means no call site has to know which surface it is rendering on.
 */
export interface SegmentRowStyles {
    /** Row wrapper: height, indent and hover surface. */
    row: string;
    /** Checkbox control. */
    checkbox: string;
    /** Row label. */
    label: string;
    /** Trailing count. */
    count: string;
    /** Text input sitting inside a segment, such as the tag or class filter fields. */
    input: string;
    /** Indent applied to non-row content, so it lines up with the rows above it. */
    contentIndent: string;
    /** Name of a range filter, e.g. "Width". */
    fieldLabel: string;
    /** Current range of a range filter, e.g. "213 – 640 px". */
    fieldValue: string;
    /** Range filter track. */
    sliderTrack: string;
    /** Range filter thumbs. */
    sliderThumb: string;
}

const SEGMENT_DENSITY_KEY = Symbol('segment-density');

const COMFORTABLE_ROW_STYLES: SegmentRowStyles = {
    row: 'width-full group flex items-center space-x-2',
    checkbox: '',
    label: 'text-base font-normal',
    count: 'text-sm text-diffuse-foreground',
    input: '',
    contentIndent: '',
    fieldLabel: 'text-md',
    fieldValue: 'text-sm text-diffuse-foreground',
    sliderTrack: '',
    sliderThumb: ''
};

const COMPACT_ROW_STYLES: SegmentRowStyles = {
    // The 22px indent lines rows up under the group title rather than under its chevron.
    row: 'group flex h-7 items-center gap-2 rounded-md pl-[22px] pr-2 hover:bg-sidebar-accent/60',
    // `box-border` keeps the 1.5px border inside the 14px box; the shadcn default puts it
    // outside, which would render an 17px control.
    checkbox:
        'box-border size-3.5 rounded-[4px] border-[1.5px] [&>div]:size-3.5 [&_svg]:size-2.5 data-[state=unchecked]:border-[hsl(var(--border-hard)/0.4)] data-[state=unchecked]:bg-black/30',
    label: 'text-[12.5px] font-normal text-diffuse-foreground',
    count: 'text-[11px] font-normal tabular-nums text-muted-foreground',
    input: 'h-7 rounded-md border-[hsl(var(--border-hard)/0.16)] bg-black/[0.28] px-[9px] py-0 text-xs md:text-xs',
    contentIndent: 'pl-[22px] pr-2',
    fieldLabel: 'text-[11.5px] text-muted-foreground',
    fieldValue: 'text-[11.5px] tabular-nums text-diffuse-foreground',
    // A 3px rail rather than the 8px default: a dozen of these stack up in a 264px column.
    // The height has to repeat the primitive's own orientation variant, or that wins.
    sliderTrack:
        "data-[orientation='horizontal']:h-[3px] rounded-[2px] bg-[hsl(var(--border-hard)/0.2)]",
    sliderThumb: 'size-2.5 border'
};

/** Applies `density` to every `Segment` rendered below the calling component. */
export function setSegmentDensity(density: SegmentDensity): void {
    setContext(SEGMENT_DENSITY_KEY, density);
}

/** Reads the density set by an ancestor, defaulting to the standalone scale. */
export function getSegmentDensity(): SegmentDensity {
    return getContext<SegmentDensity | undefined>(SEGMENT_DENSITY_KEY) ?? 'comfortable';
}

/** Row classes for the density in effect. Call once per component, at init. */
export function getSegmentRowStyles(): SegmentRowStyles {
    return getSegmentDensity() === 'compact' ? COMPACT_ROW_STYLES : COMFORTABLE_ROW_STYLES;
}
