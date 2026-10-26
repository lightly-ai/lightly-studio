<script lang="ts">
    const { label }: { label: string } = $props();
</script>

<div class="px-2 py-4 text-center text-sm text-muted-foreground">
    {#if label.length > 0}
        No annotation class matches
        <span class="break-all font-medium text-foreground">{label}</span>.
    {:else}
        This dataset has no annotation classes yet.
    {/if}
</div>
