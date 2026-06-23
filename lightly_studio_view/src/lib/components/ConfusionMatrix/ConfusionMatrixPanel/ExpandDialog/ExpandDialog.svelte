<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import ConfusionMatrix from '../../ConfusionMatrix.svelte';
    import type { ConfusionMatrix as ConfusionMatrixData } from '../../types';
    import type { ColorConfig } from '../../ClassSetDialog/types';

    interface Props {
        open: boolean;
        matrix: ConfusionMatrixData;
        color: ColorConfig;
        showLegend?: boolean;
    }

    let { open = $bindable(), matrix, color, showLegend = false }: Props = $props();
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="flex h-[92vh] max-w-[94vw] flex-col sm:max-w-[94vw]">
        <Dialog.Header>
            <Dialog.Title>Confusion matrix</Dialog.Title>
            <Dialog.Description>
                Scroll or pinch inside the chart to zoom · hover a cell for details
            </Dialog.Description>
        </Dialog.Header>
        <div class="min-h-0 flex-1 overflow-y-auto">
            <ConfusionMatrix
                {matrix}
                {showLegend}
                colorIntensity={color.intensity}
                logScale={color.logScale}
                zoomable
            />
        </div>
    </Dialog.Content>
</Dialog.Root>
