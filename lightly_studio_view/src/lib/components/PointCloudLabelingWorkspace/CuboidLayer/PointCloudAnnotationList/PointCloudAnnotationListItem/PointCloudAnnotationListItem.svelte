<script lang="ts">
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import PointCloudAnnotationDetails from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationDetails';
    import Typography from '$lib/components/Typography';
    import { ChevronDown } from '@lucide/svelte';
    import { cn } from '$lib/utils';

    interface Props {
        /** Cuboid displayed by this row. */
        cuboid: CuboidAnnotation;
        /** Display color resolved from the cuboid's annotation class. */
        color: string;
        /** Display name resolved from the cuboid's annotation class. */
        className: string;
        /** Whether this row's details are visible. */
        isSelected: boolean;
        /** Toggles the row's expanded state. */
        onToggle: (cuboidId: string) => void;
    }

    let { cuboid, color, className, isSelected, onToggle }: Props = $props();
</script>

<div
    class={cn(
        'rounded-sm transition-colors',
        isSelected ? 'border border-accent-foreground/20 bg-accent' : 'bg-card hover:bg-accent/50'
    )}
>
    <button
        type="button"
        class="flex w-full items-center gap-2 px-4 py-3 text-left"
        onclick={() => onToggle(cuboid.id)}
        aria-expanded={isSelected}
        data-testid="point-cloud-annotation-list-row"
    >
        <span
            class="size-3 shrink-0 rounded-sm"
            style="background-color: {color}"
            aria-hidden="true"
        ></span>
        <Typography variant="body2" className="flex-1 truncate">{className}</Typography>
        <ChevronDown
            class={cn(
                'size-4 shrink-0 text-muted-foreground transition-transform',
                isSelected && 'rotate-180'
            )}
        />
    </button>
    {#if isSelected}
        <div class="px-4 pb-4 pt-1">
            <PointCloudAnnotationDetails annotation={cuboid} />
        </div>
    {/if}
</div>
