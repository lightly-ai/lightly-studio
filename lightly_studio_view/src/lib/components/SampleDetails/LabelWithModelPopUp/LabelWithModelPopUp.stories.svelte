<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import LabelWithModelOverlay from '../LabelWithModelOverlay/LabelWithModelOverlay.svelte';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import ZoomPanel from '$lib/components/ZoomPanel/ZoomPanel.svelte';
    import LabelWithModelPopUp from './LabelWithModelPopUp.svelte';
    const { Story } = defineMeta({
        title: 'Sample details/Model-assisted labeling',
        component: LabelWithModelPopUp
    });
</script>

<script lang="ts">
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import type { ComponentProps } from 'svelte';
    import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { useModelSuggestionReview } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';

    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    client.setQueryData(
        readAnnotationLabelsOptions({ path: { collection_id: 'preview' } }).queryKey,
        []
    );
    const model = {
        id: 'Warehouse detector',
        task: 'object_detection' as const,
        class_names: ['person', 'box', 'forklift']
    };
    let threshold = $state(0.5);
    let generatedThreshold = $state(0.5);
    const review = useModelSuggestionReview();
    const generate = async () => {
        generatedThreshold = threshold;
        review.replace(
            model.class_names.map((class_name, index) => ({
                class_name,
                score: 0.96 - index * 0.12,
                bbox: { x: 70 + index * 110, y: 50 + index * 120, width: 90, height: 100 },
                segmentation_mask: null
            }))
        );
    };
    void generate();
    const labelWithModel: ComponentProps<typeof LabelWithModelPopUp>['labelWithModel'] = {
        review,
        get predictions() {
            return review.suggestions.map((suggestion) => suggestion.preview);
        },
        get hasUnsavedSuggestions() {
            return review.hasUnsavedSuggestions;
        },
        generationError: null,
        get needsRegeneration() {
            return generatedThreshold !== threshold;
        },
        annotationSource: 'ground_truth',
        annotationSourceBlockedReason: null,
        pendingChange: null,
        requestChange: (action) => action(),
        confirmChange: () => {},
        cancelChange: () => {},
        isGenerating: false,
        isEmptyResult: false,
        isSaving: false,
        get canSave() {
            return review.acceptedSuggestions.length > 0;
        },
        canGenerate: true,
        generate,
        clear: () => review.replace([]),
        save: async () => {
            review.acceptedSuggestions.forEach((suggestion) => review.remove(suggestion.preview));
        }
    };
</script>

<Story name="Review suggestions" asChild>
    <QueryClientProvider {client}>
        <div class="relative h-[720px] w-full bg-background p-4">
            <svg class="h-full w-full" viewBox="0 0 600 700" aria-label="Suggestion preview">
                <LabelWithModelOverlay
                    sample={{ width: 600, height: 700 }}
                    scale={1}
                    saveAs="box"
                    {labelWithModel}
                />
            </svg>
            <SteppingNavigation
                hasPrevious={true}
                hasNext={true}
                onPrevious={() => {}}
                onNext={() => {}}
            />
            <ZoomPanel scale={1} onZoomReset={() => {}} onZoomIn={() => {}} onZoomOut={() => {}}>
                {#snippet content()}
                    <LabelWithModelPopUp
                        onClose={labelWithModel.clear}
                        collectionId="preview"
                        models={[model]}
                        {model}
                        onModelChange={() => {}}
                        {threshold}
                        onThresholdChange={(value) => (threshold = value)}
                        saveAs="box"
                        onSaveAsChange={() => {}}
                        {labelWithModel}
                    />
                {/snippet}
            </ZoomPanel>
        </div>
    </QueryClientProvider>
</Story>
