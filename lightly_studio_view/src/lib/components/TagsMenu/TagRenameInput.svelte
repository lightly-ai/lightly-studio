<script lang="ts">
    import { tick } from 'svelte';
    import { Checkbox as CheckboxPrimitive } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import { Check } from '@lucide/svelte';
    import type { TagView } from '$lib/services/types';

    let {
        tag,
        renamingTagId,
        tagsSelected,
        onTagSelectionToggle,
        onSave,
        onCancel
    }: {
        tag: TagView;
        renamingTagId: string | null;
        tagsSelected: Set<string>;
        onTagSelectionToggle: (id: string) => void;
        onSave: (tag: TagView, newName: string) => void;
        onCancel: () => void;
    } = $props();

    let renameValue = $state(tag.name);
    let renameInputRef = $state<HTMLInputElement | null>(null);

    const trimmedRenameValue = $derived(renameValue.trim());
    const saveDisabled = $derived(
        renamingTagId !== null || trimmedRenameValue.length === 0 || trimmedRenameValue === tag.name
    );

    $effect(() => {
        tick().then(() => {
            renameInputRef?.focus();
            renameInputRef?.select();
        });
    });

    function handleSave(event: MouseEvent | KeyboardEvent) {
        event.stopPropagation();
        if (saveDisabled) return;
        onSave(tag, trimmedRenameValue);
    }

    function handleCancel(event?: MouseEvent) {
        event?.stopPropagation();
        onCancel();
    }
</script>

<div class="flex items-center gap-2" data-testid={`rename-tag-form-${tag.tag_id}`}>
    <CheckboxPrimitive
        checked={tagsSelected.has(tag.tag_id)}
        onCheckedChange={() => onTagSelectionToggle(tag.tag_id)}
        disabled={renamingTagId === tag.tag_id}
    />
    <Input
        bind:ref={renameInputRef}
        bind:value={renameValue}
        class="h-8 text-xs"
        data-testid={`rename-tag-input-${tag.tag_id}`}
        placeholder="Tag name"
        disabled={renamingTagId === tag.tag_id}
        onclick={(event: MouseEvent) => {
            event.stopPropagation();
        }}
        onkeydown={(event: KeyboardEvent) => {
            event.stopPropagation();
            if (event.key === 'Enter') {
                event.preventDefault();
                handleSave(event);
            }
            if (event.key === 'Escape') {
                event.preventDefault();
                handleCancel();
            }
        }}
    />
    <button
        type="button"
        class="inline-flex size-7 shrink-0 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
        data-testid={`save-tag-rename-${tag.tag_id}`}
        disabled={saveDisabled}
        onclick={handleSave}
    >
        <Check class="size-4" />
    </button>
</div>
