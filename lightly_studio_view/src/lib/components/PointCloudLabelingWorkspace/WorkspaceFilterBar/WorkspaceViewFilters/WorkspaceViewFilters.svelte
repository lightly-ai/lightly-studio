<script lang="ts">
    import { Select } from '$lib/components/Select';
    import type { ColorMode } from '$lib/components/PointCloudViewer';

    interface Props {
        referenceFrames: readonly { readonly name: string }[];
        referenceFrameId: string;
        onSelectReferenceFrame: (frameId: string) => void;
        isShowingSensorFrames: boolean;
        colorMode: Exclude<ColorMode, 'none'>;
        onColorModeChange: (colorMode: Exclude<ColorMode, 'none'>) => void;
    }

    let {
        referenceFrames,
        referenceFrameId,
        onSelectReferenceFrame,
        isShowingSensorFrames,
        colorMode,
        onColorModeChange
    }: Props = $props();

    const frameItems = $derived(
        referenceFrames.map((frame) => ({
            value: frame.name,
            label: frame.name,
            testId: `workspace-frame-select-${frame.name}`
        }))
    );
    const frameTriggerLabel = $derived(`Frame: ${referenceFrameId}`);
    const colorItems = [
        { value: 'height', label: 'Height' },
        { value: 'intensity', label: 'Intensity' },
        { value: 'distance', label: 'Distance' },
        { value: 'density', label: 'Density' },
        { value: 'height-distance', label: 'Height + Distance' },
        { value: 'height-density', label: 'Height + Density' }
    ];
    const colorTriggerLabel = $derived(
        `Color: ${colorItems.find((item) => item.value === colorMode)?.label ?? colorMode}`
    );
</script>

{#if referenceFrames.length > 0}
    <Select
        items={frameItems}
        value={referenceFrameId}
        triggerLabel={frameTriggerLabel}
        size="xs"
        class="w-40"
        testId="workspace-frame-select"
        onValueChange={onSelectReferenceFrame}
    />
    {#if isShowingSensorFrames}
        <span class="text-xs text-muted-foreground" data-testid="workspace-frame-fallback">
            No transform at this tick. Showing sensor frames.
        </span>
    {/if}
{/if}
<Select
    items={colorItems}
    value={colorMode}
    triggerLabel={colorTriggerLabel}
    size="xs"
    class="w-40"
    testId="workspace-color-select"
    onValueChange={(value) => onColorModeChange(value as Exclude<ColorMode, 'none'>)}
/>
