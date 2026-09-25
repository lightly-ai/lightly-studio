<script lang="ts">
    import { PaneResizer } from 'paneforge';
    import { GripHorizontal, GripVertical } from '@lucide/svelte';

    interface Props {
        /** Direction of the pane group the resizer separates. */
        direction: 'horizontal' | 'vertical';
    }

    let { direction }: Props = $props();
</script>

<!-- Same grip as the collection layout's side-panel resizer. -->
{#if direction === 'horizontal'}
    <PaneResizer class="relative mx-2 flex w-1 cursor-col-resize items-center justify-center">
        <div class="bg-brand z-10 flex h-7 min-w-5 items-center justify-center">
            <GripVertical class="text-diffuse-foreground" />
        </div>
    </PaneResizer>
{:else}
    <PaneResizer class="relative my-2 flex h-1 cursor-row-resize items-center justify-center">
        <div class="bg-brand z-10 flex h-5 min-w-7 items-center justify-center">
            <GripHorizontal class="text-diffuse-foreground" />
        </div>
    </PaneResizer>
{/if}
