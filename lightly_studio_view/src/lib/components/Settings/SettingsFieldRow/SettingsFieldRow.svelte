<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Label } from '$lib/components/ui/label';

    interface Props {
        id: string;
        label: string;
        children: Snippet;
    }

    const { id, label, children }: Props = $props();
</script>

<div class="grid grid-cols-2 items-center gap-4">
    <Label for={id} class="text-right text-foreground">
        {label}
    </Label>
    {@render children()}
</div>
