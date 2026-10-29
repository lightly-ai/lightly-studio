<script lang="ts">
    import { tick, untrack } from 'svelte';
    import { Checkbox as CheckboxPrimitive } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import { Check } from '@lucide/svelte';
    import { Button } from '$lib/components';

    let {
        id,
        name,
        kind,
        renamingId,
        checked,
        onCheckedChange,
        onSave,
        onCancel
    }: {
        id: string;
        name: string;
        /** What the item is, as users read it, e.g. "tag" or "annotation source". */
        kind: string;
        renamingId: string | null;
        checked: boolean;
        onCheckedChange: () => void;
        onSave: (newName: string) => void;
        onCancel: () => void;
    } = $props();

    let renameValue = $state(untrack(() => name));
    let renameInputRef = $state<HTMLInputElement | null>(null);

    const testIdKind = $derived(kind.replaceAll(' ', '-'));
    const placeholder = $derived(`${kind.charAt(0).toUpperCase()}${kind.slice(1)} name`);
    const trimmedRenameValue = $derived(renameValue.trim());
    const saveDisabled = $derived(
        renamingId !== null || trimmedRenameValue.length === 0 || trimmedRenameValue === name
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
        onSave(trimmedRenameValue);
    }

    function handleCancel(event?: MouseEvent) {
        event?.stopPropagation();
        onCancel();
    }
</script>

<div class="flex items-center gap-2" data-testid={`rename-${testIdKind}-form-${id}`}>
    <CheckboxPrimitive {checked} {onCheckedChange} disabled={renamingId === id} />
    <Input
        bind:ref={renameInputRef}
        bind:value={renameValue}
        class="h-8 text-xs"
        data-testid={`rename-${testIdKind}-input-${id}`}
        {placeholder}
        isPending={renamingId === id}
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
    <Button
        icon={Check}
        ariaLabel={`Save ${kind} rename`}
        isPending={renamingId === id}
        buttonProps={{
            class: 'size-7 p-0',
            'data-testid': `save-${testIdKind}-rename-${id}`,
            disabled: saveDisabled,
            onclick: handleSave
        }}
    />
</div>
