<script lang="ts">
    import { Button } from '$lib/components';
    import { Pencil, Trash2 } from '@lucide/svelte';

    interface Props {
        name: string;
        onRename: () => void;
        onDelete: () => void;
    }

    const { name, onRename, onDelete }: Props = $props();
</script>

<div
    class="flex text-muted-foreground opacity-60 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
>
    <Button
        variant="ghost"
        icon={Pencil}
        ariaLabel={`Rename ${name}`}
        buttonProps={{ type: 'button', size: 'icon', class: 'size-8', onclick: onRename }}
    />
    <Button
        variant="ghost"
        icon={Trash2}
        ariaLabel={`Delete ${name}`}
        buttonProps={{
            type: 'button',
            size: 'icon',
            class: 'size-8 hover:text-destructive',
            onclick: onDelete
        }}
    />
</div>
