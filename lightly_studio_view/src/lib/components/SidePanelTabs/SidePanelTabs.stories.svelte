<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import SidePanelTabs from './SidePanelTabs.svelte';

    const { Story } = defineMeta({
        title: 'Components/SidePanelTabs',
        component: SidePanelTabs,
        tags: ['autodocs'],
        argTypes: {
            isImages: { control: 'boolean' },
            isEvaluationMatches: { control: 'boolean' },
            hasMediaWithEmbeddings: { control: 'boolean' },
            hasEvaluationRuns: { control: 'boolean' }
        }
    });
</script>

<Story
    name="All Tabs"
    args={{
        isImages: true,
        isEvaluationMatches: false,
        hasMediaWithEmbeddings: true,
        hasEvaluationRuns: true
    }}
/>

<Story
    name="Embeddings Only"
    args={{
        isImages: false,
        isEvaluationMatches: false,
        hasMediaWithEmbeddings: true,
        hasEvaluationRuns: false
    }}
/>

<Story
    name="Images No Embeddings"
    args={{
        isImages: true,
        isEvaluationMatches: false,
        hasMediaWithEmbeddings: false,
        hasEvaluationRuns: false
    }}
/>

<Story
    name="Images With Evaluation Runs"
    args={{
        isImages: true,
        isEvaluationMatches: false,
        hasMediaWithEmbeddings: false,
        hasEvaluationRuns: true
    }}
/>

<Story
    name="Matches With Evaluation Runs"
    args={{
        isImages: false,
        isEvaluationMatches: true,
        hasMediaWithEmbeddings: false,
        hasEvaluationRuns: true
    }}
/>

<Story
    name="No Tabs"
    args={{
        isImages: false,
        isEvaluationMatches: false,
        hasMediaWithEmbeddings: false,
        hasEvaluationRuns: false
    }}
/>
