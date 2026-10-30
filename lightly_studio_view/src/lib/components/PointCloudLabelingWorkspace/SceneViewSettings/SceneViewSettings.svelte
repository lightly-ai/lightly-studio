<script lang="ts">
    import { Settings2 } from '@lucide/svelte';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import type { ComponentProps } from 'svelte';
    import AccumulationSettings from './AccumulationSettings.svelte';
    import PointSizeSettings from './PointSizeSettings.svelte';

    interface Props {
        showOrthographicViews: boolean;
        pointSize: number;
        showNavigationHelpers: boolean;
        showAnnotationTooltips: boolean;
        disabled?: boolean;
        accumulation?: ComponentProps<typeof AccumulationSettings>;
        onToggle: (showOrthographicViews: boolean) => void;
        onPointSizeChange: (pointSize: number) => void;
        onToggleNavigationHelpers: (show: boolean) => void;
        onToggleAnnotationTooltips: (show: boolean) => void;
    }

    let {
        showOrthographicViews,
        pointSize,
        showNavigationHelpers,
        showAnnotationTooltips,
        disabled = false,
        accumulation,
        onToggle,
        onPointSizeChange,
        onToggleNavigationHelpers,
        onToggleAnnotationTooltips
    }: Props = $props();
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
        <PointSizeSettings {pointSize} {disabled} {onPointSizeChange} />
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
        {#if accumulation}
            <AccumulationSettings
                accumulatePointClouds={accumulation.accumulatePointClouds}
                accumulationRadius={accumulation.accumulationRadius}
                setAccumulatePointClouds={accumulation.setAccumulatePointClouds}
                setAccumulationRadius={accumulation.setAccumulationRadius}
            />
        {/if}
    </Popover.Content>
</Popover.Root>
