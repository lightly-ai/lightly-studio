<script lang="ts">
    import { Settings2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Label } from '$lib/components/ui/label';
    import { Slider } from '$lib/components/ui/slider';
    import { Switch } from '$lib/components/ui/switch';
    import * as Popover from '$lib/components/ui/popover';
    import type { ProjectionSettings } from './projectionSettings';

    interface Props {
        settings: ProjectionSettings;
        onChange: (settings: ProjectionSettings) => void;
    }

    let { settings, onChange }: Props = $props();
    let open = $state(false);

    const update = (changes: Partial<ProjectionSettings>) => onChange({ ...settings, ...changes });
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="xs"
                aria-label="Projection settings"
                aria-expanded={open}
            >
                <Settings2 />
                Settings
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-72 space-y-4 p-4">
        <div class="space-y-1">
            <h3 class="text-sm font-medium">Camera projection settings</h3>
            <p class="text-xs text-muted-foreground">Adjust the camera overlay visibility.</p>
        </div>
        <div class="flex items-center justify-between">
            <Label for="projection-points">Show points</Label>
            <Switch
                id="projection-points"
                checked={settings.showPoints}
                onCheckedChange={(checked: boolean) => update({ showPoints: checked })}
                data-testid="projection-show-points"
            />
        </div>
        <div class="flex items-center justify-between">
            <Label for="projection-annotations">Show annotations</Label>
            <Switch
                id="projection-annotations"
                checked={settings.showAnnotations}
                onCheckedChange={(checked: boolean) => update({ showAnnotations: checked })}
                data-testid="projection-show-annotations"
            />
        </div>
        <div class="space-y-2">
            <div class="flex justify-between text-xs">
                <Label for="projection-point-size">Point size</Label>
                <span class="tabular-nums text-muted-foreground">{settings.pointSize}px</span>
            </div>
            <Slider
                id="projection-point-size"
                type="single"
                value={settings.pointSize}
                min={1}
                max={10}
                step={1}
                onValueChange={(value: number) => update({ pointSize: value })}
                aria-label="Projection point size"
            />
        </div>
        <div class="space-y-2">
            <div class="flex justify-between text-xs">
                <Label for="projection-point-opacity">Point opacity</Label>
                <span class="tabular-nums text-muted-foreground">
                    {Math.round(settings.pointOpacity * 100)}%
                </span>
            </div>
            <Slider
                id="projection-point-opacity"
                type="single"
                value={settings.pointOpacity}
                min={0.1}
                max={1}
                step={0.05}
                onValueChange={(value: number) => update({ pointOpacity: value })}
                aria-label="Projection point opacity"
            />
        </div>
        <label class="flex items-center justify-between text-sm" for="projection-color-mode">
            Color points by
            <select
                id="projection-color-mode"
                class="h-8 rounded-md border bg-background px-2 text-xs"
                value={settings.colorMode}
                onchange={(event) =>
                    update({
                        colorMode: (event.currentTarget as HTMLSelectElement)
                            .value as ProjectionSettings['colorMode']
                    })}
            >
                <option value="depth">Depth</option>
                <option value="height">Height</option>
                <option value="intensity">Intensity</option>
                <option value="rgb">RGB</option>
                <option value="single">Single color</option>
            </select>
        </label>
        {#if settings.colorMode === 'single'}
            <label class="flex items-center justify-between text-sm" for="projection-point-color">
                Point color
                <select
                    id="projection-point-color"
                    class="h-8 rounded-md border bg-background px-2 text-xs"
                    value={settings.pointColor}
                    onchange={(event) =>
                        update({ pointColor: (event.currentTarget as HTMLSelectElement).value })}
                >
                    <option value="#22d3ee">Cyan</option>
                    <option value="#facc15">Yellow</option>
                    <option value="#ffffff">White</option>
                </select>
            </label>
        {/if}
    </Popover.Content>
</Popover.Root>
