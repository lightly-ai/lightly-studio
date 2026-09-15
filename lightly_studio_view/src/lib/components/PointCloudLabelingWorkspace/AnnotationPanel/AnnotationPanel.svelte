<script lang="ts">
    import { ListTree } from '@lucide/svelte';

    /** Placeholder for the annotation list, class assignment, and inspector. */
</script>

<div
    class="flex h-full flex-col items-center justify-center gap-2 border-l bg-background text-muted-foreground"
    data-testid="workspace-annotation-panel"
>
    <ListTree class="size-6" aria-hidden="true" />
    <p class="text-sm">Annotations</p>
</div>
