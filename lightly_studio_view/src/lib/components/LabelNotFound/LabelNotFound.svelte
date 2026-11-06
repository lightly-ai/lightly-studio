<script lang="ts">
    const { label, canCreate = true }: { label: string; canCreate?: boolean } = $props();
</script>

{#if !canCreate}
    <div class="text-md m-2">No class found.</div>
{:else if label.length > 0}
    <div class="text-md m-2">
        Press Enter to create a new <span class="font-semibold">"{label}"</span> annotation class.
    </div>
{:else}
    <div class="text-md m-2">Type to create a new annotation class.</div>
{/if}
