<script lang="ts">
    import GridHeader from './GridHeader.svelte';

    let { testCase = 'children-only' }: { testCase?: string } = $props();
</script>

{#if testCase === 'children-only'}
    <GridHeader>Test Title</GridHeader>
{:else if testCase === 'no-image-size-control'}
    <GridHeader showImageSizeControl={false}>Test Title</GridHeader>
{:else if testCase === 'with-aux-controls'}
    <GridHeader>
        Test
        {#snippet auxControls()}
            Aux Controls
        {/snippet}
    </GridHeader>
{:else if testCase === 'with-selection-controls'}
    <GridHeader>
        Main Content
        {#snippet selectionControls()}
            Selection Controls
        {/snippet}
    </GridHeader>
{:else if testCase === 'all-elements'}
    <GridHeader showImageSizeControl={true}>
        Main Content
        {#snippet selectionControls()}
            Selection Controls
        {/snippet}
        {#snippet auxControls()}
            Extra Controls
        {/snippet}
    </GridHeader>
{/if}
