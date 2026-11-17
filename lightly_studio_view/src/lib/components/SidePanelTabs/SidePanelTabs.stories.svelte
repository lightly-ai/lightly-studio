<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import SidePanelTabs from './SidePanelTabs.svelte';

    const { Story } = defineMeta({
        title: 'Components/SidePanelTabs',
        component: SidePanelTabs,
        tags: ['autodocs'],
        argTypes: {
            supportsQuery: { control: 'boolean' },
            hasMediaWithEmbeddings: { control: 'boolean' },
            supportsEvaluation: { control: 'boolean' },
            supportsDistribution: { control: 'boolean' }
        }
    });
</script>

<Story
    name="All Tabs"
    args={{
        supportsQuery: true,
        hasMediaWithEmbeddings: true,
        supportsEvaluation: true,
        supportsDistribution: true
    }}
/>

<Story
    name="Embeddings Only"
    args={{
        supportsQuery: false,
        hasMediaWithEmbeddings: true,
        supportsEvaluation: false,
        supportsDistribution: false
    }}
/>

<Story
    name="Images No Embeddings"
    args={{
        supportsQuery: true,
        hasMediaWithEmbeddings: false,
        supportsEvaluation: false,
        supportsDistribution: true
    }}
/>

<Story
    name="Images With Evaluation"
    args={{
        supportsQuery: true,
        hasMediaWithEmbeddings: false,
        supportsEvaluation: true,
        supportsDistribution: true
    }}
/>

<Story
    name="No Tabs"
    args={{
        supportsQuery: false,
        hasMediaWithEmbeddings: false,
        supportsEvaluation: false,
        supportsDistribution: false
    }}
/>
