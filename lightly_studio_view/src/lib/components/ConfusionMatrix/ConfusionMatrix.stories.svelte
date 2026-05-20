<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ConfusionMatrix from './ConfusionMatrix.svelte';

    const { Story } = defineMeta({
        title: 'Components/ConfusionMatrix',
        component: ConfusionMatrix,
        tags: ['autodocs']
    });
</script>

<script lang="ts">
    import {
        cocoLikePairings,
        empty,
        large20Classes,
        medium8Classes,
        singleClass,
        small3Classes
    } from './fixtures';
    import { Slider } from '$lib/components/ui/slider';
    import { DEFAULT_THRESHOLDS } from './types';

    let confValue = $state([DEFAULT_THRESHOLDS.confidence]);
    let iouValue = $state([DEFAULT_THRESHOLDS.iou]);

    const smallArgs = { data: { kind: 'matrix' as const, matrix: small3Classes } };
    const mediumArgs = { data: { kind: 'matrix' as const, matrix: medium8Classes } };
    const largeArgs = { data: { kind: 'matrix' as const, matrix: large20Classes } };
    const emptyData = { kind: 'matrix' as const, matrix: empty };
    const singleClassData = { kind: 'matrix' as const, matrix: singleClass };
</script>

<Story name="Small (3 classes)" args={smallArgs} />

<Story name="Medium (8 classes)" args={mediumArgs} />

<Story name="Large (20 classes)" args={largeArgs} />

<Story name="Empty" args={{ data: emptyData }} />

<Story name="Single class" args={{ data: singleClassData }} />

<Story
    name="No predictions above threshold"
    args={{
        data: {
            kind: 'pairings',
            pairings: cocoLikePairings,
            thresholds: { confidence: 0.99, iou: 0.5 }
        }
    }}
/>

<Story name="With threshold controls" asChild>
    <div class="space-y-4">
        <div class="flex flex-col gap-3 rounded-md bg-muted/40 p-3 text-sm">
            <div class="flex items-center gap-3">
                <span class="w-24">Confidence ≥</span>
                <div class="w-48">
                    <Slider type="multiple" min={0} max={1} step={0.05} bind:value={confValue} />
                </div>
                <span class="min-w-10 text-right font-medium tabular-nums">
                    {confValue[0].toFixed(2)}
                </span>
            </div>
            <div class="flex items-center gap-3">
                <span class="w-24">IoU ≥</span>
                <div class="w-48">
                    <Slider type="multiple" min={0} max={1} step={0.05} bind:value={iouValue} />
                </div>
                <span class="min-w-10 text-right font-medium tabular-nums">
                    {iouValue[0].toFixed(2)}
                </span>
            </div>
        </div>
        <ConfusionMatrix
            data={{
                kind: 'pairings',
                pairings: cocoLikePairings,
                thresholds: { confidence: confValue[0], iou: iouValue[0] }
            }}
        />
    </div>
</Story>

<Story name="With threshold controls and legend" asChild>
    <div class="space-y-4">
        <div class="flex flex-col gap-3 rounded-md bg-muted/40 p-3 text-sm">
            <div class="flex items-center gap-3">
                <span class="w-24">Confidence ≥</span>
                <div class="w-48">
                    <Slider type="multiple" min={0} max={1} step={0.05} bind:value={confValue} />
                </div>
                <span class="min-w-10 text-right font-medium tabular-nums">
                    {confValue[0].toFixed(2)}
                </span>
            </div>
            <div class="flex items-center gap-3">
                <span class="w-24">IoU ≥</span>
                <div class="w-48">
                    <Slider type="multiple" min={0} max={1} step={0.05} bind:value={iouValue} />
                </div>
                <span class="min-w-10 text-right font-medium tabular-nums">
                    {iouValue[0].toFixed(2)}
                </span>
            </div>
        </div>
        <ConfusionMatrix
            showLegend
            data={{
                kind: 'pairings',
                pairings: cocoLikePairings,
                thresholds: { confidence: confValue[0], iou: iouValue[0] }
            }}
        />
    </div>
</Story>
