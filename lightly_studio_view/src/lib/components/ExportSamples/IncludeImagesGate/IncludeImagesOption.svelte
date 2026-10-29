<script lang="ts">
    import { Checkbox } from '$lib/components';
    import {
        exportImagesEstimate,
        type ExportImagesEstimateResponse,
        type ImageFilter
    } from '$lib/api/lightly_studio_local';
    import { getIncludeImagesState } from './includeImagesGate';

    interface Props {
        /** The image collection being exported. */
        collectionId: string;
        /** The filter the export applies. */
        imageFilter: ImageFilter | null;
        /** Whether the images are bundled with the annotations. Bindable. */
        includeImages: boolean;
    }

    let { collectionId, imageFilter, includeImages = $bindable() }: Props = $props();

    let estimate = $state<ExportImagesEstimateResponse | undefined>(undefined);
    const gate = $derived(getIncludeImagesState(estimate));

    $effect(() => {
        const controller = new AbortController();
        estimate = undefined;
        exportImagesEstimate({
            path: { collection_id: collectionId },
            body: { image_filter: imageFilter },
            signal: controller.signal
        })
            .then((response) => {
                if (!controller.signal.aborted) estimate = response.data ?? undefined;
            })
            .catch(() => {
                // Without an estimate the option stays available, as before.
            });
        return () => controller.abort();
    });

    $effect(() => {
        if (!gate.allowed) includeImages = false;
    });
</script>

<Checkbox
    name="export-include-images"
    label="Include images"
    helperText="Download the images and the annotations in one zip file, ready to train on."
    isChecked={includeImages}
    disabled={!gate.allowed}
    onCheckedChange={(checked) => (includeImages = checked === true)}
/>
{#if gate.sizeText}
    <p class="mt-1 text-xs text-muted-foreground" data-testid="export-images-size">
        {gate.sizeText}
    </p>
{/if}
{#if gate.reason}
    <p class="mt-1 text-xs text-muted-foreground">{gate.reason}</p>
{/if}
