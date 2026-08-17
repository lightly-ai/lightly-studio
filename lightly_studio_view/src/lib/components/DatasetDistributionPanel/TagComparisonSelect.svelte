<script lang="ts">
    import { Check, ChevronDown } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Command from '$lib/components/ui/command';
    import * as Popover from '$lib/components/ui/popover';
    import type { SelectItem } from '$lib/components/Select';
    import { cn } from '$lib/utils';

    interface Props {
        items: SelectItem[];
        selectedIds: string[];
        onChange: (ids: string[]) => void;
    }

    const { items, selectedIds, onChange }: Props = $props();
    let open = $state(false);
    const label = $derived(
        selectedIds.length === 0
            ? 'Compare sample tags'
            : `${selectedIds.length} tag${selectedIds.length === 1 ? '' : 's'} selected`
    );

    const toggle = (id: string) =>
        onChange(
            selectedIds.includes(id)
                ? selectedIds.filter((selectedId) => selectedId !== id)
                : [...selectedIds, id]
        );
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        <Button
            variant="outline"
            size="sm"
            class="m-0 h-8 min-w-0 flex-1 justify-start gap-2 rounded-md px-3 text-xs font-normal"
            role="combobox"
            aria-expanded={open}
            data-testid="dataset-distribution-tag-select"
        >
            <span class="truncate">{label}</span>
            <ChevronDown class="ml-auto size-4 shrink-0 opacity-50" />
        </Button>
    </Popover.Trigger>
    <Popover.Content class="w-[260px] p-0">
        <Command.Root>
            <Command.Input placeholder="Search sample tags..." />
            <Command.List class="max-h-[240px] dark:[color-scheme:dark]">
                <Command.Empty>No sample tag found.</Command.Empty>
                <Command.Group>
                    {#each items as item (item.value)}
                        <Command.Item
                            value={item.label}
                            data-testid={`dataset-distribution-tag-option-${item.value}`}
                            onSelect={() => toggle(item.value)}
                        >
                            <Check
                                class={cn(!selectedIds.includes(item.value) && 'text-transparent')}
                            />
                            <span class="min-w-0 flex-1 truncate">{item.label}</span>
                        </Command.Item>
                    {/each}
                </Command.Group>
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
