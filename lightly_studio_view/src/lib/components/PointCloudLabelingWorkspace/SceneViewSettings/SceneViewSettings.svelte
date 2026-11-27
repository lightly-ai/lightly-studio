<script lang="ts">
    import Settings2 from '@lucide/svelte/icons/settings-2';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import type { ComponentProps, Snippet } from 'svelte';
    import AccumulationSettings from './AccumulationSettings.svelte';
    import PointSizeSettings from './PointSizeSettings.svelte';

    interface Props {
        pointSize: number;
        showNavigationHelpers: boolean;
        disabled?: boolean;
        accumulation?: ComponentProps<typeof AccumulationSettings>;
        onPointSizeChange: (pointSize: number) => void;
        onToggleNavigationHelpers: (show: boolean) => void;
        /** Controls shown above the display settings, such as the frame and color selects. */
        filters?: Snippet;
    }

    let {
        pointSize,
        showNavigationHelpers,
        disabled = false,
        accumulation,
        onPointSizeChange,
        onToggleNavigationHelpers,
        filters
    }: Props = $props();
    let open = $state(false);
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="ghost"
                size="xs"
                class="h-7 gap-1 px-2"
                title="Scene settings"
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
        {#if filters}
            <div class="border-b pb-3">{@render filters()}</div>
        {/if}
        <PointSizeSettings {pointSize} {disabled} {onPointSizeChange} />
        <label class="flex items-center gap-2 border-t pt-3 text-sm">
            <Checkbox
                checked={showNavigationHelpers}
                aria-label="Show navigation helpers"
                onCheckedChange={(checked) => onToggleNavigationHelpers(checked === true)}
            />
            <span>Show navigation helpers</span>
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
