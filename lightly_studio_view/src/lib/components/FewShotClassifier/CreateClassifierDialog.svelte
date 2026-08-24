<script lang="ts">
    import { page } from '$app/state';
    import { Alert, Button } from '$lib/components';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { useClassifierState } from '$lib/hooks/useClassifiers/useClassifierState';
    import { useClassifierWorkflow } from '$lib/hooks/useClassifiers/useClassifierWorkflow';
    import { CLASSIFIER_CREATION_CANDIDATE_LIMIT } from '$lib/hooks/useClassifiers/classifierCandidates';
    import ClassifierSamplesGrid from './ClassifierSamplesGrid.svelte';

    interface Props {
        onCancel: () => void;
    }

    const { onCancel }: Props = $props();
    const { createClassifier } = useClassifiers();
    const { classifierSelectedSampleIds } = useClassifierState();
    const { setPending } = useClassifierWorkflow();
    const collectionId = page.params.collection_id!;
    let classifierName = $state('');
    let isSubmitting = $state(false);
    let submitError = $state<string | null>(null);
    let displayedSampleCount = $state(CLASSIFIER_CREATION_CANDIDATE_LIMIT);
    const isFormValid = $derived(
        classifierName.trim().length > 0 && $classifierSelectedSampleIds.size > 0
    );

    async function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || isSubmitting) return;

        isSubmitting = true;
        setPending(true);
        submitError = null;
        try {
            await createClassifier({
                name: classifierName.trim(),
                class_list: ['positive', 'negative'],
                collection_id: collectionId
            });
        } catch (error) {
            submitError = error instanceof Error ? error.message : String(error);
        } finally {
            isSubmitting = false;
            setPending(false);
        }
    }
</script>

<div class="flex min-h-0 flex-1 flex-col gap-4">
    {#if submitError}
        <Alert title="Failed to create classifier">{submitError}</Alert>
    {/if}
    <div class="flex items-center gap-4">
        <Label for="classifier-name" class="whitespace-nowrap text-left text-foreground">
            What do you want to find?
        </Label>
        <Input
            id="classifier-name"
            type="text"
            bind:value={classifierName}
            class="flex-1"
            placeholder="For example, zebras or damaged products"
            required
            disabled={isSubmitting}
            data-testid="classifier-name-input"
        />
    </div>
    <div class="flex min-h-0 flex-1 flex-col border-t pt-4">
        <div class="mb-4 space-y-1">
            <div class="flex items-center justify-between gap-4">
                <h3 class="text-lg font-semibold">Choose matching examples</h3>
                <span class="text-sm text-muted-foreground">
                    {$classifierSelectedSampleIds.size} selected · {displayedSampleCount} shown
                </span>
            </div>
            <p class="text-sm text-muted-foreground">
                Choose a few clear examples from these {displayedSampleCount} candidates. You do not need
                to select every matching image.
            </p>
        </div>
        <div class="min-h-0 w-full flex-1 overflow-y-auto rounded-lg border">
            <ClassifierSamplesGrid
                collection_id={collectionId}
                source="collection"
                sampleLimit={CLASSIFIER_CREATION_CANDIDATE_LIMIT}
                onDisplayedSampleCountChange={(count) => (displayedSampleCount = count)}
            />
        </div>
    </div>
    <div class="flex justify-end gap-2">
        <Button
            variant="outline"
            buttonProps={{
                onclick: onCancel,
                disabled: isSubmitting,
                'data-testid': 'classifier-dialog-cancel'
            }}>Cancel</Button
        >
        <Button
            isPending={isSubmitting}
            variant="default"
            buttonProps={{
                onclick: handleFormSubmit,
                disabled: !isFormValid || isSubmitting,
                'data-testid': 'classifier-dialog-submit'
            }}
        >
            {isSubmitting ? 'Training...' : 'Train Classifier'}
        </Button>
    </div>
</div>
