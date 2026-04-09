<script lang="ts">
    import { Plus } from '@lucide/svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import type { TagView } from '$lib/services/types';

    interface Props {
        options: TagView[];
        attachedTagNames: Set<string>;
        busy: boolean;
        onSelect: (name: string) => void;
    }

    let { options, attachedTagNames, busy, onSelect }: Props = $props();

    let open = $state(false);
    let inputValue = $state('');

    $effect(() => {
        if (!open) inputValue = '';
    });

    function handleSelect(name: string) {
        onSelect(name);
        open = false;
    }

    const showCreate = $derived(
        inputValue.trim() !== '' &&
            !attachedTagNames.has(inputValue.trim().toLowerCase()) &&
            !options.some((t) => t.name.toLowerCase() === inputValue.trim().toLowerCase())
    );
</script>

<Popover.Root bind:open>
    <Popover.Trigger
        class="mt-2 flex items-center gap-1 rounded px-1 py-0.5 text-xs text-muted-foreground transition hover:text-foreground"
        disabled={busy}
    >
        <Plus class="size-3" />
        Add tag
    </Popover.Trigger>
    <Popover.Content class="w-48 p-0" side="right" align="start">
        <Command.Root>
            <Command.Input placeholder="Tag name…" bind:value={inputValue} disabled={busy} />
            <Command.List>
                <Command.Empty>No tags found</Command.Empty>
                <Command.Group>
                    {#each options as opt (opt.tag_id)}
                        <Command.Item value={opt.name} onSelect={() => handleSelect(opt.name)}>
                            {opt.name}
                        </Command.Item>
                    {/each}
                </Command.Group>
                {#if showCreate}
                    <div class="border-t">
                        <Command.Item
                            value="__create__"
                            onSelect={() => handleSelect(inputValue)}
                            forceMount
                            keywords={[]}
                        >
                            <span class="opacity-50">Create:</span>
                            <span class="ml-1 font-semibold">{inputValue.trim()}</span>
                        </Command.Item>
                    </div>
                {/if}
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
