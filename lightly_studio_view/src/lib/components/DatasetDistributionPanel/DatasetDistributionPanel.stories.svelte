<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import DatasetDistributionPanel from './DatasetDistributionPanel.svelte';

    const { Story } = defineMeta({
        title: 'Components/DatasetDistributionPanel',
        component: DatasetDistributionPanel,
        tags: ['autodocs'],
        args: { topN: 20 },
        argTypes: {
            topN: { control: { type: 'number', min: 1, max: 80, step: 1 } }
        }
    });
</script>

<script lang="ts">
    import { GripVertical } from '@lucide/svelte';
    import { Pane, PaneGroup, PaneResizer } from 'paneforge';
    import { balanced, empty, longLabels, longTail, many80Classes } from '../BarChart/fixtures';
    import { exampleSources, numericMetadataSources } from './sourceFixtures';
</script>

{#snippet sidePanel(args)}
    <!-- Mimics the right side-panel width (~35% pane) from the collection layout. -->
    <div class="h-[480px] w-[420px]">
        <DatasetDistributionPanel {...args} />
    </div>
{/snippet}

<Story name="Balanced (5 classes)" args={{ data: balanced }} template={sidePanel} />

<Story name="Long-tail imbalance (30 classes)" args={{ data: longTail }} template={sidePanel} />

<Story
    name="Many classes (80, horizontal scroll)"
    args={{ data: many80Classes }}
    template={sidePanel}
/>

<Story name="Long labels (truncation)" args={{ data: longLabels }} template={sidePanel} />

<Story name="Empty" args={{ data: empty }} template={sidePanel} />

<Story name="With close button" args={{ data: balanced, onClose: () => {} }} template={sidePanel} />

<!-- Prototype: one panel, multiple sources. Switch between class labels, tags,
     metadata keys (secondary key picker), and eval via the Source selector —
     shows how the same UI/UX generalises beyond class labels. -->
<Story
    name="Multi-source (class / tags / metadata / eval)"
    args={{ sources: exampleSources, title: 'Distribution', onClose: () => {} }}
    template={sidePanel}
/>

<!-- Numeric metadata keys carry histogram bins instead of category counts, so
     the panel renders the Histogram component and hides the categorical
     controls (sort / top-N / orientation). Switching to "weather" swaps back
     to the categorical bar chart. -->
<Story
    name="Numeric metadata histogram"
    args={{
        sources: numericMetadataSources,
        title: 'Distribution',
        onClose: () => {}
    }}
    template={sidePanel}
/>

<!-- Mirrors the PaneGroup structure of the collection +layout.svelte: main
     content pane + resizer + side panel pane, so the panel can be reviewed
     at realistic, resizable proportions. -->
<Story name="In collection layout" args={{ data: many80Classes, onClose: () => {} }}>
    {#snippet template(args)}
        <div class="flex h-[600px] w-full">
            <PaneGroup direction="horizontal" class="min-w-0 flex-1">
                <Pane defaultSize={65} minSize={35} class="flex">
                    <div
                        class="relative flex min-w-0 flex-1 flex-col rounded-[1vw] bg-card p-4 pb-2"
                    >
                        <div
                            class="flex h-full items-center justify-center text-sm text-muted-foreground"
                        >
                            Sample grid (main content)
                        </div>
                    </div>
                </Pane>
                <PaneResizer
                    class="relative mx-2 flex w-1 cursor-col-resize items-center justify-center"
                >
                    <div class="bg-brand z-10 flex h-7 min-w-5 items-center justify-center">
                        <GripVertical class="text-diffuse-foreground" />
                    </div>
                </PaneResizer>
                <Pane defaultSize={35} minSize={25} class="flex min-h-0 flex-col">
                    <DatasetDistributionPanel {...args} />
                </Pane>
            </PaneGroup>
        </div>
    {/snippet}
</Story>
