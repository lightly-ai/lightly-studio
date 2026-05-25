<script lang="ts">
    interface Props {
        strategyLabels: string[];
    }

    let { strategyLabels }: Props = $props();
</script>

{#if strategyLabels.length > 1}
    <p class="text-sm text-muted-foreground" data-testid="selection-summary">
        Selection will combine {strategyLabels.length} strategies: {strategyLabels.join(', ')}.
    </p>
{/if}
