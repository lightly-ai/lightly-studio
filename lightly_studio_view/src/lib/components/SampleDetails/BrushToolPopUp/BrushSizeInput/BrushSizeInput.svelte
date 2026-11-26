<script lang="ts">
    import { MAX_BRUSH_SIZE, MIN_BRUSH_SIZE } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { untrack } from 'svelte';
    import {
        SLIDER_STEPS,
        brushSizeToSliderPosition,
        clampBrushSize,
        parseBrushSize,
        sliderPositionToBrushSize
    } from '../brushSize';

    interface Props {
        size: number;
        onChange: (size: number) => void;
    }

    let { size, onChange }: Props = $props();

    const ARROW_STEP = 1;
    const SHIFT_ARROW_STEP = 10;

    let draft = $state('');
    $effect(() => {
        draft = String(size);
    });

    // Moved only when the size changes from outside, so the thumb does not jump while dragging.
    let sliderPosition = $state(0);
    $effect(() => {
        const positionSize = sliderPositionToBrushSize(untrack(() => sliderPosition));
        if (positionSize !== size) sliderPosition = brushSizeToSliderPosition(size);
    });

    const applySize = (nextSize: number) => {
        draft = String(nextSize);
        if (nextSize !== size) onChange(nextSize);
    };

    const applyDraft = () => {
        const parsedSize = parseBrushSize(draft);
        if (parsedSize === undefined) {
            draft = String(size);
            return;
        }
        applySize(parsedSize);
    };

    const stepSize = (event: KeyboardEvent, direction: number) => {
        event.preventDefault();
        const step = event.shiftKey ? SHIFT_ARROW_STEP : ARROW_STEP;
        const baseSize = parseBrushSize(draft) ?? size;
        applySize(clampBrushSize(baseSize + direction * step));
    };

    const onFieldKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter') applyDraft();
        else if (event.key === 'ArrowUp') stepSize(event, 1);
        else if (event.key === 'ArrowDown') stepSize(event, -1);
    };

    const onSliderInput = (event: Event & { currentTarget: HTMLInputElement }) => {
        sliderPosition = Number(event.currentTarget.value);
        applySize(sliderPositionToBrushSize(sliderPosition));
    };
</script>

<div class="flex w-full flex-col gap-2">
    <div class="flex items-center">
        <span class="w-16 text-sm text-muted-foreground"> Size: </span>
        <input
            type="number"
            min={MIN_BRUSH_SIZE}
            max={MAX_BRUSH_SIZE}
            step="1"
            inputmode="numeric"
            aria-label="Brush size in pixels"
            value={draft}
            oninput={(event) => (draft = event.currentTarget.value)}
            onkeydown={onFieldKeyDown}
            onblur={applyDraft}
            class="h-8 w-16 rounded-md border border-input bg-background px-1 text-right text-sm text-foreground"
        />
        <span class="ml-1 text-sm text-muted-foreground">px</span>
    </div>
    <input
        type="range"
        min="0"
        max={SLIDER_STEPS}
        step="1"
        aria-label="Brush size"
        value={sliderPosition}
        oninput={onSliderInput}
        class="w-full accent-primary"
    />
</div>
