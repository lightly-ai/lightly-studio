<script lang="ts">
    import { LayoutList } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import * as Popover from '$lib/components/ui/popover';
    import { resolveTileFields, useTileFields } from '$lib/hooks/useTileFields/useTileFields';
    import { filterTileFieldGroups, getTileFieldOptions } from './getTileFieldOptions';

    type OptionsParams = Parameters<typeof getTileFieldOptions>[0];

    interface Props {
        collectionId: string;
        isAnnotations: boolean;
        metadataKeys: string[];
        tags?: OptionsParams['tags'];
        sources?: OptionsParams['sources'];
        compact?: boolean;
    }

    const {
        collectionId,
        isAnnotations,
        metadataKeys,
        tags = [],
        sources = [],
        compact = false
    }: Props = $props();

    const { tileFields, toggleTileField, clearTileFields } = useTileFields();
    const ticked = $derived(resolveTileFields($tileFields[collectionId], isAnnotations));
    let search = $state('');
    const groups = $derived(
        filterTileFieldGroups(
            getTileFieldOptions({ isAnnotations, metadataKeys, tags, sources }),
            search
        )
    );
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

<!-- Each opening starts with an empty search, also after switching grids. -->
<Popover.Root onOpenChange={(open) => open && (search = '')}>
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
    <Popover.Content class="flex max-h-96 w-64 flex-col p-1" align="end">
        <Input
            value={search}
            oninput={(event) => (search = event.currentTarget.value)}
            placeholder="Search fields…"
            aria-label="Search fields"
            class="h-8"
            wrapperClass="mb-1 shrink-0"
        />
        <div class="min-h-0 flex-1 overflow-y-auto">
            {#each groups as group (group.label)}
                <div class="px-2 pb-1 pt-2 text-xs font-medium text-muted-foreground">
                    {group.label}
                </div>
                {#each group.options as option (option.id)}
                    {@render optionRow(option)}
                {/each}
            {:else}
                <div class="px-2 py-2 text-sm text-muted-foreground">No matching fields</div>
            {/each}
        </div>
        {#if ticked.length > 0}
            <Button
                variant="ghost"
                buttonProps={{
                    size: 'sm',
                    class: 'mt-1 w-full shrink-0 justify-start text-xs',
                    onclick: () => clearTileFields(collectionId)
                }}
            >
                Clear all
            </Button>
        {/if}
    </Popover.Content>
</Popover.Root>
