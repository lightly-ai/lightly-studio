<script lang="ts">
    import { page } from '$app/state';
    import { Alert } from '$lib/components';
    import { useClassifierState } from '$lib/hooks/useClassifiers/useClassifierState';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { useClassifierWorkflow } from '$lib/hooks/useClassifiers/useClassifierWorkflow';
    import { useClassifiersMenu } from '$lib/hooks/useClassifiers/useClassifiersMenu';
    import { get } from 'svelte/store';
    import { toast } from 'svelte-sonner';
    import ClassifierSamplesGrid from './ClassifierSamplesGrid.svelte';
    import ClassifierRefinementActions from './ClassifierRefinementActions.svelte';
    import ReviewAgreementSummary from './ReviewAgreementSummary.svelte';
    import { calculateReviewAgreement } from './reviewAgreement';

    interface Props {
        onCancel: () => void;
        onFinish: () => void;
    }

    const { onCancel, onFinish }: Props = $props();
    const { workflow, recordReview, setPending } = useClassifierWorkflow();
    const { classifierSamples, classifierSelectedSampleIds } = useClassifierState();
    const {
        applyClassifierCorrections,
        commitTempClassifier,
        refineClassifier,
        showClassifierTrainingSamples
    } = useClassifiers();
    const { openClassifiersMenu, switchToManageTab, scrollToAndSelectClassifier } =
        useClassifiersMenu();
    const collectionId = page.params.collection_id!;
    let pendingAction = $state<'continue' | 'finish' | null>(null);
    const isSubmitting = $derived(pendingAction !== null);
    let isShowingTrainingSamples = $state(false);
    let submitError = $state<string | null>(null);

    async function handleRefineClassifier() {
        if (isSubmitting || !$workflow.classifierId) return;

        const predictions = get(classifierSamples);
        const agreement =
            predictions && !isShowingTrainingSamples
                ? calculateReviewAgreement(predictions, get(classifierSelectedSampleIds))
                : null;
        pendingAction = 'continue';
        setPending(true);
        submitError = null;
        try {
            await refineClassifier(
                $workflow.classifierId,
                collectionId,
                $workflow.classifierClasses
            );
            if (agreement) recordReview(agreement.confirmedPredictions, agreement.reviewedSamples);
            isShowingTrainingSamples = false;
        } catch (error) {
            submitError = error instanceof Error ? error.message : String(error);
        } finally {
            pendingAction = null;
            setPending(false);
        }
    }

    async function handleFinishClassifier() {
        if (isSubmitting || !$workflow.classifierId) return;

        pendingAction = 'finish';
        setPending(true);
        submitError = null;
        try {
            await applyClassifierCorrections($workflow.classifierId);
            if ($workflow.mode === 'temp') await saveTemporaryClassifier();
            onFinish();
        } catch (error) {
            submitError = error instanceof Error ? error.message : String(error);
        } finally {
            pendingAction = null;
            setPending(false);
        }
    }

    async function saveTemporaryClassifier() {
        const classifierId = $workflow.classifierId!;
        await commitTempClassifier(classifierId, collectionId);
        toast.success(`Classifier "${$workflow.classifierName}" created successfully.`);
        openClassifiersMenu();
        switchToManageTab();
        scrollToAndSelectClassifier(classifierId);
    }

    async function handleShowTrainingSamples(checked: boolean) {
        if (!$workflow.classifierId) return;
        submitError = null;
        try {
            await showClassifierTrainingSamples(
                $workflow.classifierId,
                collectionId,
                $workflow.classifierClasses,
                checked
            );
            isShowingTrainingSamples = checked;
        } catch (error) {
            submitError = error instanceof Error ? error.message : String(error);
        }
    }
</script>

<div class="flex min-h-0 flex-1 flex-col gap-4">
    {#if submitError}<Alert title="Operation failed">{submitError}</Alert>{/if}
    <ReviewAgreementSummary
        confirmedPredictions={$workflow.confirmedPredictions}
        reviewedSamples={$workflow.reviewedSamples}
        latestConfirmedPredictions={$workflow.latestConfirmedPredictions}
        latestReviewedSamples={$workflow.latestReviewedSamples}
    />
    <div class="flex min-h-0 flex-1 flex-col border-t pt-4">
        <h3 class="mb-3 text-lg font-semibold">
            {isShowingTrainingSamples ? 'Edit Training History' : 'Review Predictions'}
        </h3>
        <div class="min-h-0 w-full flex-1 overflow-y-auto rounded-lg border">
            <ClassifierSamplesGrid collection_id={collectionId} />
        </div>
    </div>
    <ClassifierRefinementActions
        mode={$workflow.mode}
        {pendingAction}
        canSubmit={Boolean($classifierSamples)}
        {isShowingTrainingSamples}
        onShowTrainingSamplesChange={handleShowTrainingSamples}
        {onCancel}
        onContinue={handleRefineClassifier}
        onFinish={handleFinishClassifier}
    />
</div>
