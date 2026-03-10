<script lang="ts">
    import LayoutCard from './LayoutCard.svelte';

    let { content = '', className }: { content?: string; className?: string } = $props();
</script>

<LayoutCard {className}>
    {#snippet children()}
        <div>{content}</div>
    {/snippet}
</LayoutCard>
