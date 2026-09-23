<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import SidePanelTabs from './SidePanelTabs.svelte';

    const { Story } = defineMeta({
        title: 'Components/SidePanelTabs',
        component: SidePanelTabs,
        tags: ['autodocs'],
        argTypes: {
            isImages: { control: 'boolean' },
            hasMediaWithEmbeddings: { control: 'boolean' },
            supportsEvaluation: { control: 'boolean' },
            supportsDistribution: { control: 'boolean' }
        }
    });
</script>

<Story
    name="All Tabs"
    args={{
        isImages: true,
        hasMediaWithEmbeddings: true,
        supportsEvaluation: true,
        supportsDistribution: true
    }}
/>

<Story
    name="Embeddings Only"
    args={{
        isImages: false,
        hasMediaWithEmbeddings: true,
        supportsEvaluation: false,
        supportsDistribution: false
    }}
/>

<Story
    name="Images No Embeddings"
    args={{
        isImages: true,
        hasMediaWithEmbeddings: false,
        supportsEvaluation: false,
        supportsDistribution: true
    }}
/>

<Story
    name="Images With Evaluation"
    args={{
        isImages: true,
        hasMediaWithEmbeddings: false,
        supportsEvaluation: true,
        supportsDistribution: true
    }}
/>

<Story
    name="No Tabs"
    args={{
        isImages: false,
        hasMediaWithEmbeddings: false,
        supportsEvaluation: false,
        supportsDistribution: false
    }}
/>
