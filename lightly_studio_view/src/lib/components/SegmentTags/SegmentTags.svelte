<script lang="ts">
    import { Segment } from '$lib/components';
    import { TagsIcon, Plus } from '@lucide/svelte';
    import { SampleType } from '$lib/api/lightly_studio_local';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useAddTagToSample } from '$lib/hooks/useAddTagToSample/useAddTagToSample.svelte.js';

    interface TagItem {
        tag_id?: string;
        name: string;
    }

    interface Props {
        tags: TagItem[];
        collectionId?: string;
        sampleId?: string;
        onRemoveTag?: (tagId: string) => Promise<void>;
        onClick?: (tagId: string) => Promise<void>;
        onRefetch?: () => void;
    }

    let {
        tags,
        collectionId = '',
        sampleId = '',
        onRemoveTag,
        onClick,
        onRefetch = () => {}
    }: Props = $props();

    const removeTagHandler = onRemoveTag ?? onClick ?? (async () => undefined);

    const { collections } = useGlobalStorage();
    const tagKind = $derived(
        $collections[collectionId]?.sampleType === SampleType.ANNOTATION ? 'annotation' : 'sample'
    );

    const { tags: allCollectionTags, loadTags } = $derived(
        useTags({ collection_id: collectionId, kind: [tagKind] })
    );

    const addTag = useAddTagToSample({
        collectionId,
        sampleId,
        getTagKind: () => tagKind,
        getTags: () => tags,
        getAllCollectionTags: () => $allCollectionTags,
        onRefetch,
        onTagsRefetch: () => loadTags()
    });

    let open = $state(false);
    let inputValue = $state('');

    $effect(() => {
        if (!open) inputValue = '';
    });

    function handleSelect(name: string) {
        const existing = addTag.options.find(
            (t) => t.name.toLowerCase() === name.toLowerCase()
        );
        if (existing) {
            void addTag.addExisting(existing);
        } else {
            void addTag.createAndAdd(name);
        }
        open = false;
    }
</script>

<Segment title="Tags" icon={TagsIcon}>
    <div class="flex flex-wrap gap-1">
        {#each tags as tag (tag.tag_id)}
            <div class="inline-flex items-center gap-1 rounded-lg bg-card px-2 py-1 text-xs">
                <span data-testid="segment-tag-name">{tag.name}</span>
                <button
                    type="button"
                    class="flex size-4 items-center justify-center rounded-full text-muted-foreground transition hover:text-destructive focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label={`Remove tag ${tag.name}`}
                    data-testid={`remove-tag-${tag.name}`}
                    onclick={(event) => {
                        event.stopPropagation();
                        if (tag.tag_id) void removeTagHandler(tag.tag_id);
                    }}
                >
                    x
                </button>
            </div>
        {/each}
    </div>

    <Popover.Root bind:open>
        <Popover.Trigger
            class="mt-2 flex items-center gap-1 rounded px-1 py-0.5 text-xs text-muted-foreground transition hover:text-foreground"
            disabled={addTag.busy}
        >
            <Plus class="size-3" />
            Add tag
        </Popover.Trigger>
        <Popover.Content class="w-48 p-0" side="right" align="start">
            <Command.Root>
                <Command.Input
                    placeholder="Tag name…"
                    bind:value={inputValue}
                    disabled={addTag.busy}
                />
                <Command.List>
                    <Command.Empty>No tags found</Command.Empty>
                    <Command.Group>
                        {#each addTag.options as opt (opt.tag_id)}
                            <Command.Item
                                value={opt.name}
                                onSelect={() => handleSelect(opt.name)}
                            >
                                {opt.name}
                            </Command.Item>
                        {/each}
                    </Command.Group>
                    {#if inputValue.trim() && addTag.options.some((t) => t.name.toLowerCase() === inputValue.trim().toLowerCase()) === false}
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
</Segment>
