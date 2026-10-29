<script lang="ts">
    import { LayoutList } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import * as Popover from '$lib/components/ui/popover';
    import { resolveTileFields, useTileFields } from '$lib/hooks/useTileFields/useTileFields';
    import { getTileFieldOptions } from './getTileFieldOptions';

    interface Props {
        collectionId: string;
        isAnnotations: boolean;
        metadataKeys: string[];
        compact?: boolean;
    }

    const { collectionId, isAnnotations, metadataKeys, compact = false }: Props = $props();

    const { tileFields, toggleTileField, clearTileFields } = useTileFields();
    const ticked = $derived(resolveTileFields($tileFields[collectionId], isAnnotations));
    const options = $derived(getTileFieldOptions({ isAnnotations, metadataKeys }));
</script>

{#snippet optionRow(option: { id: string; label: string })}
    <label
        class="flex min-h-8 cursor-pointer items-center gap-2 rounded px-2 text-sm hover:bg-accent"
    >
        <Checkbox
            checked={ticked.includes(option.id)}
            onCheckedChange={() => toggleTileField(collectionId, option.id, isAnnotations)}
        />
        <span class="truncate" title={option.label}>{option.label}</span>
    </label>
{/snippet}

<Popover.Root>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                variant="ghost"
                icon={LayoutList}
                ariaLabel="Show on tiles"
                buttonProps={{ ...props, size: 'sm', 'data-testid': 'tile-fields-trigger' }}
            >
                {#if !compact}
                    Show on tiles{ticked.length > 0 ? ` (${ticked.length})` : ''}
                {/if}
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="max-h-96 w-64 overflow-y-auto p-1" align="end">
        {#each options.fields as option (option.id)}
            {@render optionRow(option)}
        {/each}
        {#if options.metadata.length > 0}
            <div class="px-2 pb-1 pt-2 text-xs font-medium text-muted-foreground">Metadata</div>
            {#each options.metadata as option (option.id)}
                {@render optionRow(option)}
            {/each}
        {/if}
        {#if ticked.length > 0}
            <Button
                variant="ghost"
                buttonProps={{
                    size: 'sm',
                    class: 'mt-1 w-full justify-start text-xs',
                    onclick: () => clearTileFields(collectionId)
                }}
            >
                Clear all
            </Button>
        {/if}
    </Popover.Content>
</Popover.Root>
