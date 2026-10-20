<script lang="ts">
    import { Settings2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Label } from '$lib/components/ui/label';
    import { Select } from '$lib/components/Select';
    import { Slider } from '$lib/components/ui/slider';
    import { Switch } from '$lib/components/ui/switch';
    import * as Popover from '$lib/components/ui/popover';
    import type { ProjectionSettings } from './projectionSettings';

    interface Props {
        settings: ProjectionSettings;
        onChange: (settings: ProjectionSettings) => void;
        onPlaybackToggle?: () => void;
    }

    let { settings, onChange, onPlaybackToggle }: Props = $props();
    let open = $state(false);

    const update = (changes: Partial<ProjectionSettings>) => onChange({ ...settings, ...changes });
    const colorItems = [
        { value: 'height', label: 'Height' },
        { value: 'intensity', label: 'Intensity' },
        { value: 'distance', label: 'Distance' },
        { value: 'density', label: 'Density' },
        { value: 'height-distance', label: 'Height + Distance' },
        { value: 'height-density', label: 'Height + Density' }
    ];
    const preventSpaceActivation = (event: KeyboardEvent) => {
        if (event.code !== 'Space' || event.repeat) return;
        event.preventDefault();
        event.stopPropagation();
        onPlaybackToggle?.();
        (event.target as HTMLElement).blur();
        setTimeout(() => {
            (document.activeElement as HTMLElement | null)?.blur();
        }, 0);
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="xs"
                class="px-3"
                aria-label="Projection settings"
                aria-expanded={open}
                onkeydown={preventSpaceActivation}
            >
                <Settings2 />
                Settings
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content
        class="max-h-[calc(100vh-2rem)] w-72 space-y-4 overflow-y-auto p-4"
        onkeydown={preventSpaceActivation}
    >
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
        <div class="flex items-center justify-between gap-3 text-sm">
            <Label for="projection-color-mode">Color points by</Label>
            <Select
                items={colorItems}
                value={settings.colorMode}
                size="xs"
                class="min-w-0 flex-1"
                selectProps={{
                    id: 'projection-color-mode',
                    onkeydown: preventSpaceActivation
                }}
                onValueChange={(value) =>
                    update({ colorMode: value as ProjectionSettings['colorMode'] })}
            />
        </div>
    </Popover.Content>
</Popover.Root>
