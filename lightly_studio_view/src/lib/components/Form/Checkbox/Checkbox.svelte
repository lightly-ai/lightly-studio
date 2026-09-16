<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { getSegmentRowStyles } from '$lib/components/Segment/segmentDensity';
    import { cn } from '$lib/utils';
    import type { ComponentProps } from 'svelte';

    const {
        name,
        label,
        onCheckedChange,
        isChecked = false,
        helperText,
        disabled = false
    }: {
        name: string;
        label: string;
        onCheckedChange?: ComponentProps<typeof Checkbox>['onCheckedChange'];
        isChecked?: boolean;
        helperText?: string;
        disabled?: boolean;
    } = $props();

    const rowStyles = getSegmentRowStyles();
</script>

<div class="flex min-w-0 flex-col gap-2">
    <div class={cn('flex min-w-0 gap-2', rowStyles.row)}>
        <Checkbox
            id={name}
            aria-labelledby={`${name}-label`}
            checked={isChecked}
            class={rowStyles.checkbox}
            {onCheckedChange}
            {disabled}
        />
        <Label
            id={`${name}-label`}
            for={name}
            class={cn(
                'min-w-0 flex-1 truncate text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
                rowStyles.label
            )}
            data-testid="tags-menu-label"
            title={label}
        >
            {label}
        </Label>
    </div>
    {#if helperText}
        <div class="text-xs text-muted-foreground">
            {helperText}
        </div>
    {/if}
</div>
