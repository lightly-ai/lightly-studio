<script lang="ts">
    import * as Command from '$lib/components/ui/command/index.js';
    import { Check, Minus } from '@lucide/svelte';

    interface Props {
        tags: Array<{ tag_id: string; name: string }>;
        tagStates: Record<string, 'checked' | 'indeterminate' | 'unchecked'>;
        busy: boolean;
        /** Explains that the states only describe the loaded targets, when that applies. */
        knownTargetNote?: string;
        onToggle: (tagId: string) => void;
        onCreate: (name: string) => void;
    }

    let { tags, tagStates, busy, knownTargetNote, onToggle, onCreate }: Props = $props();

    let query = $state('');

    const trimmedQuery = $derived(query.trim());
    const showCreate = $derived(
        trimmedQuery !== '' &&
            !tags.some((tag) => tag.name.toLowerCase() === trimmedQuery.toLowerCase())
    );

    function handleToggle(tagId: string) {
        if (busy) return;
        onToggle(tagId);
    }

    function handleCreate() {
        if (busy) return;
        onCreate(trimmedQuery);
        query = '';
    }
</script>

<Command.Root>
    <Command.Input placeholder="Search tags…" bind:value={query} disabled={busy} />
    <Command.List>
        <Command.Empty>No tags found</Command.Empty>
        <Command.Group>
            {#each tags as tag (tag.tag_id)}
                {@const state = tagStates[tag.tag_id] ?? 'unchecked'}
                <Command.Item
                    value={tag.name}
                    onSelect={() => handleToggle(tag.tag_id)}
                    role="menuitemcheckbox"
                    aria-checked={state === 'indeterminate' ? 'mixed' : state === 'checked'}
                    data-testid={`context-menu-tag-${tag.name}`}
                >
                    {#if state === 'checked'}
                        <Check aria-hidden="true" />
                    {:else if state === 'indeterminate'}
                        <Minus aria-hidden="true" />
                    {:else}
                        <span class="size-4 shrink-0"></span>
                    {/if}
                    <span class="truncate">{tag.name}</span>
                </Command.Item>
            {/each}
        </Command.Group>
        {#if showCreate}
            <div class="border-t">
                <Command.Item
                    value="__create__"
                    onSelect={handleCreate}
                    forceMount
                    keywords={[]}
                    data-testid="context-menu-create-tag"
                >
                    <span class="opacity-50">Create:</span>
                    <span class="ml-1 truncate font-semibold">{trimmedQuery}</span>
                </Command.Item>
            </div>
        {/if}
    </Command.List>
    {#if knownTargetNote}
        <p class="border-t px-2 py-1.5 text-xs text-muted-foreground">{knownTargetNote}</p>
    {/if}
</Command.Root>
