<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import SidePanelTabs from './SidePanelTabs.svelte';

    const { Story } = defineMeta({
        title: 'Components/SidePanelTabs',
        component: SidePanelTabs,
        tags: ['autodocs'],
        argTypes: {
            hasMediaWithEmbeddings: { control: 'boolean' },
            supportsEvaluation: { control: 'boolean' },
            supportsDistribution: { control: 'boolean' },
            supportsQuery: { control: 'boolean' }
        }
    });
</script>

<Story
    name="All Tabs"
    args={{
        hasMediaWithEmbeddings: true,
        supportsEvaluation: true,
        supportsDistribution: true,
        supportsQuery: true
    }}
/>

<Story
    name="Embeddings Only"
    args={{
        hasMediaWithEmbeddings: true,
        supportsEvaluation: false,
        supportsDistribution: false,
        supportsQuery: false
    }}
/>

<Story
    name="Images No Embeddings"
    args={{
        hasMediaWithEmbeddings: false,
        supportsEvaluation: false,
        supportsDistribution: true,
        supportsQuery: true
    }}
/>

<Story
    name="Images With Evaluation"
    args={{
        hasMediaWithEmbeddings: false,
        supportsEvaluation: true,
        supportsDistribution: true,
        supportsQuery: true
    }}
/>

<Story
    name="No Tabs"
    args={{
        hasMediaWithEmbeddings: false,
        supportsEvaluation: false,
        supportsDistribution: false,
        supportsQuery: false
    }}
/>
