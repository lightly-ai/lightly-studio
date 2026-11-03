<script lang="ts">
    import { Copy, Ellipsis, ImageUp } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';
    import * as Popover from '$lib/components/ui/popover';

    interface Props {
        /** The selected IDs, or null when the selection is a select-all filter. */
        ids: string[] | null;
        /** Searches for images like the selected one; absent when that is not possible. */
        onFindSimilar?: () => void;
    }
    let { ids, onFindSimilar }: Props = $props();

    let open = $state(false);
    const hasItems = $derived(ids !== null || onFindSimilar !== undefined);
    const itemClass =
        'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent';

    async function copyIds() {
        open = false;
        if (!ids) return;
        try {
            await navigator.clipboard.writeText(ids.join('\n'));
            toast.success(`Copied ${ids.length} ${ids.length === 1 ? 'ID' : 'IDs'}`);
        } catch {
            toast.error('Failed to copy the IDs.');
        }
    }

    function findSimilar() {
        open = false;
        onFindSimilar?.();
    }
</script>

{#if hasItems}
    <Popover.Root bind:open>
        <Popover.Trigger
            class="inline-flex size-8 items-center justify-center rounded-md hover:bg-accent"
            aria-label="More actions"
        >
            <Ellipsis class="size-4" />
        </Popover.Trigger>
        <Popover.Content class="w-52 p-1" align="end" side="top">
            {#if onFindSimilar}
                <button class={itemClass} onclick={findSimilar}>
                    <ImageUp class="size-4" /> Find similar images
                </button>
            {/if}
            {#if ids}
                <button class={itemClass} onclick={copyIds}>
                    <Copy class="size-4" /> Copy IDs
                </button>
            {/if}
        </Popover.Content>
    </Popover.Root>
{/if}
