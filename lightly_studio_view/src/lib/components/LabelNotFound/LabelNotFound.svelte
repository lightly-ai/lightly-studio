<script lang="ts">
    const { label }: { label: string } = $props();
</script>

<div class="text-md m-2">
    {#if label.length > 0}
        No annotation class <span class="font-semibold">"{label}"</span>.
    {:else}
        No annotation classes yet.
    {/if}
    Add annotation classes in the settings.
</div>
