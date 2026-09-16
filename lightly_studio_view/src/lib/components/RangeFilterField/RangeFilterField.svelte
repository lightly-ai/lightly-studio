<script lang="ts">
    import { getSegmentDensity, getSegmentRowStyles } from '$lib/components/Segment/segmentDensity';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import { cn } from '$lib/utils';

    interface Props {
        /** Field name, e.g. "Width". */
        label: string;
        /** Formatted lower bound of the current range, e.g. "213px". */
        minText: string;
        /** Formatted upper bound of the current range, e.g. "640px". */
        maxText: string;
        min: number;
        max: number;
        step?: number;
        value: [number, number];
        onValueCommit: (values: number[]) => void;
        /** Class on the slider root, used by tests to target a specific filter. */
        sliderClass?: string;
    }

    const { label, minText, maxText, min, max, step, value, onValueCommit, sliderClass }: Props =
        $props();

    const styles = getSegmentRowStyles();
    const isCompact = getSegmentDensity() === 'compact';
</script>

<div class={isCompact ? '' : 'space-y-1'}>
    {#if isCompact}
        <!-- Name and range share one line here; a 264px rail has no room for a heading of
             its own, and long metadata keys would wrap instead of truncating. -->
        <div class="mb-1.5 flex items-baseline justify-between gap-2">
            <span class={cn('min-w-0 truncate', styles.fieldLabel)} title={label}>{label}</span>
            <span class={cn('shrink-0', styles.fieldValue)}>{minText} – {maxText}</span>
        </div>
    {:else}
        <h2 class={styles.fieldLabel}>{label}</h2>
        <div class={cn('flex justify-between', styles.fieldValue)}>
            <span>{minText}</span>
            <span>{maxText}</span>
        </div>
    {/if}
    <div class={isCompact ? 'relative' : 'relative p-2'}>
        <Slider
            type="multiple"
            class={sliderClass}
            trackClass={styles.sliderTrack}
            thumbClass={styles.sliderThumb}
            {min}
            {max}
            {step}
            {value}
            {onValueCommit}
        />
    </div>
</div>
