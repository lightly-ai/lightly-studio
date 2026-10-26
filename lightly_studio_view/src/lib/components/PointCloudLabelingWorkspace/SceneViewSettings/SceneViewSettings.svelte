<script lang="ts">
    import { Settings2 } from '@lucide/svelte';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Button } from '$lib/components/ui/button';
    import { Slider } from '$lib/components/ui/slider';
    import * as Popover from '$lib/components/ui/popover';

    import type { SceneViewSettingsProps } from './sceneViewSettingsProps';

    let {
        showOrthographicViews,
        pointSize,
        showNavigationHelpers,
        showAnnotationTooltips,
        disabled = false,
        onToggle,
        onPointSizeChange,
        onToggleNavigationHelpers,
        onToggleAnnotationTooltips
    }: SceneViewSettingsProps = $props();
    let open = $state(false);
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="xs"
                class="px-3"
                aria-label="Scene settings"
                aria-expanded={open}
            >
                <Settings2 />
                Settings
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-64 space-y-4 p-3" align="end">
        <div class="space-y-1">
            <h3 class="text-sm font-medium">Scene settings</h3>
            <p class="text-xs text-muted-foreground">Adjust the scene display.</p>
        </div>
        <label class="flex items-center gap-2 text-sm">
            <Checkbox
                checked={showOrthographicViews}
                {disabled}
                aria-label="Show orthographic projections"
                onCheckedChange={(checked) => onToggle(checked === true)}
            />
            <span>Show orthographic projections</span>
        </label>
        <div class="space-y-2 border-t pt-3">
            <div class="flex items-center justify-between text-sm">
                <span>Point size</span>
                <span class="tabular-nums text-muted-foreground">{pointSize}</span>
            </div>
            <Slider
                type="single"
                value={pointSize}
                min={1}
                max={10}
                step={0.5}
                {disabled}
                aria-label="Point size"
                onValueChange={(value) => onPointSizeChange(value)}
            />
        </div>
        <label class="flex items-center gap-2 border-t pt-3 text-sm">
            <Checkbox
                checked={showNavigationHelpers}
                aria-label="Show navigation helpers"
                onCheckedChange={(checked) => onToggleNavigationHelpers(checked === true)}
            />
            <span>Show navigation helpers</span>
        </label>
        <label class="flex items-center gap-2 border-t pt-3 text-sm">
            <Checkbox
                checked={showAnnotationTooltips}
                aria-label="Show annotation tooltips"
                onCheckedChange={(checked) => onToggleAnnotationTooltips(checked === true)}
            />
            <span>Show annotation tooltips</span>
        </label>
    </Popover.Content>
</Popover.Root>
