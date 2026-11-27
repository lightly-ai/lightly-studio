<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import { MAX_EGO_RANGE_RADIUS, MIN_EGO_RANGE_RADIUS } from '../EgoRange';

    interface Props {
        enabled: boolean;
        /** Radius of the range, in meters. */
        radius: number;
        /** Frame attached to the ego, e.g. a vehicle or a robot; null if no default frame exists. */
        egoFrame: string | null;
        egoFrameOptions: readonly string[];
        onEnabledChange: (enabled: boolean) => void;
        onRadiusChange: (radius: number) => void;
        onEgoFrameChange: (frame: string) => void;
    }

    let {
        enabled,
        radius,
        egoFrame,
        egoFrameOptions,
        onEnabledChange,
        onRadiusChange,
        onEgoFrameChange
    }: Props = $props();

    function handleRadiusChange(event: Event & { currentTarget: HTMLInputElement }): void {
        const input = event.currentTarget;
        // An empty field converts to 0, which is not a radius that the user typed.
        const isEmpty = input.value.trim() === '';
        const value = Number(input.value);
        if (isEmpty || !Number.isFinite(value)) {
            input.value = String(radius);
            return;
        }
        onRadiusChange(value);
    }
</script>

<div class="space-y-2 border-t pt-3 dark:[color-scheme:dark]">
    <label class="flex items-center gap-2 text-sm">
        <Checkbox
            aria-label="Show ego range"
            checked={enabled}
            onCheckedChange={(checked) => onEnabledChange(checked === true)}
        />
        <span>Show ego range</span>
    </label>
    {#if enabled}
        <label class="flex items-center justify-between gap-2 text-sm">
            <span>Radius (m)</span>
            <Input
                type="number"
                class="h-7 w-20"
                min={MIN_EGO_RANGE_RADIUS}
                max={MAX_EGO_RANGE_RADIUS}
                value={radius}
                aria-label="Radius (m)"
                onchange={handleRadiusChange}
            />
        </label>
        <label class="flex items-center justify-between gap-2 text-sm">
            <span>Ego frame</span>
            <select
                class="h-7 w-28 rounded-md border bg-background px-1 text-sm"
                aria-label="Ego frame"
                value={egoFrame ?? ''}
                onchange={(event) => onEgoFrameChange(event.currentTarget.value)}
            >
                {#if !egoFrame}
                    <option value="" disabled>Pick a frame</option>
                {/if}
                {#each egoFrameOptions as frame (frame)}
                    <option value={frame}>{frame}</option>
                {/each}
            </select>
        </label>
    {/if}
</div>
