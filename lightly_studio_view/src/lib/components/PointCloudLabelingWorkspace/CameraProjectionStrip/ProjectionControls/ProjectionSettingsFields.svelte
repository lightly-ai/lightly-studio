<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Select } from '$lib/components/Select';
    import { Slider } from '$lib/components/ui/slider';
    import { Switch } from '$lib/components/ui/switch';
    import type { ProjectionSettings } from '../projectionSettings';

    interface Props {
        settings: ProjectionSettings;
        onChange: (settings: ProjectionSettings) => void;
        onKeydown: (event: KeyboardEvent) => void;
    }

    let { settings, onChange, onKeydown }: Props = $props();
    const colorItems = [
        { value: 'height', label: 'Height' },
        { value: 'intensity', label: 'Intensity' },
        { value: 'distance', label: 'Distance' },
        { value: 'density', label: 'Density' },
        { value: 'height-distance', label: 'Height + Distance' },
        { value: 'height-density', label: 'Height + Density' }
    ];

    const update = (changes: Partial<ProjectionSettings>) => onChange({ ...settings, ...changes });
</script>

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
        <Label for="projection-point-opacity">Point visibility</Label>
        <span class="tabular-nums text-muted-foreground"
            >{Math.round(settings.pointOpacity * 100)}%</span
        >
    </div>
    <Slider
        id="projection-point-opacity"
        type="single"
        value={settings.pointOpacity}
        min={0.1}
        max={1}
        step={0.05}
        onValueChange={(value: number) => update({ pointOpacity: value })}
        aria-label="Projection point visibility"
    />
</div>
<div class="flex items-center justify-between gap-3 text-sm">
    <Label for="projection-color-mode">Color points by</Label>
    <Select
        items={colorItems}
        value={settings.colorMode}
        size="xs"
        class="min-w-0 flex-1"
        selectProps={{ id: 'projection-color-mode', onkeydown: onKeydown }}
        onValueChange={(value) => update({ colorMode: value as ProjectionSettings['colorMode'] })}
    />
</div>
