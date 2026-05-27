<script lang="ts">
    const { label }: { label: string } = $props();
</script>

{#if label.length > 0}
    <div class="text-md m-2">
        Press Enter to create a new <span class="font-semibold">"{label}"</span> annotation class.
    </div>
{:else}
    <div class="text-md m-2">Type to create a new annotation class.</div>
{/if}
