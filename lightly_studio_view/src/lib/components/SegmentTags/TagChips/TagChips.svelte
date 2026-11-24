<script lang="ts">
    import { Button } from '$lib/components';
    import X from '@lucide/svelte/icons/x';
    import type { TagItem } from '../types';

    interface Props {
        tags: readonly TagItem[];
        /** Shows a remove button per tag when given. Without it, the chips are read-only. */
        onRemove?: (tagId: string) => void;
        /** Tags whose removal is pending. */
        removingTagIds?: ReadonlySet<string>;
    }

    let { tags, onRemove, removingTagIds = new Set() }: Props = $props();
</script>

<div class="flex flex-wrap gap-1">
    {#each tags as tag, index (tag.tag_id ?? `${tag.name}-${index}`)}
        <div
            class="inline-flex min-w-0 max-w-full items-center gap-1 rounded-lg bg-card px-2 py-1 text-xs"
        >
            <span class="truncate" title={tag.name} data-testid="segment-tag-name">{tag.name}</span>
            {#if onRemove && tag.tag_id}
                <Button
                    icon={X}
                    ariaLabel={`Remove tag ${tag.name}`}
                    isPending={removingTagIds.has(tag.tag_id)}
                    buttonProps={{
                        size: 'sm',
                        class: 'size-6 shrink-0 rounded-full p-1 text-muted-foreground hover:text-destructive-text',
                        'data-testid': `remove-tag-${tag.name}`,
                        onclick: (event) => {
                            event.stopPropagation();
                            onRemove(tag.tag_id!);
                        }
                    }}
                />
            {/if}
        </div>
    {/each}
</div>
