<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Button } from '$lib/components';
    import NamePicker from './NamePicker/NamePicker.svelte';
    import ExistingClassCounts from './ExistingClassCounts/ExistingClassCounts.svelte';
    import ConfirmApplyDialog from './ConfirmApplyDialog/ConfirmApplyDialog.svelte';
    import { summarizeApply, withSelectedOption } from './BulkAnnotationClassPanel.helpers';

    interface AnnotationClassOption {
        id: string;
        name: string;
    }

    interface SelectionClassCount {
        className: string;
        sampleCount: number;
    }

    interface Props {
        /** Number of selected images the annotation class is added to. */
        selectedCount: number;
        /** Annotation classes to choose from; a new name can also be typed. */
        annotationClasses: AnnotationClassOption[];
        /** Annotation sources to choose from; a new name can also be typed. */
        annotationSources: string[];
        /** Annotation source the new annotations are written to. */
        selectedSource: string;
        /** Annotation classes the selected images already have in `selectedSource`. */
        selectionClassCounts: SelectionClassCount[];
        isLoadingCounts: boolean;
        isApplying: boolean;
        onSourceChange: (source: string) => void;
        onApply: (args: { className: string; source: string }) => void;
    }

    const {
        selectedCount,
        annotationClasses,
        annotationSources,
        selectedSource,
        selectionClassCounts,
        isLoadingCounts,
        isApplying,
        onSourceChange,
        onApply
    }: Props = $props();

    let className = $state('');
    let isConfirming = $state(false);

    const sourceOptions = $derived(withSelectedOption(annotationSources, selectedSource));
    const classOptions = $derived(
        withSelectedOption(
            annotationClasses.map((option) => option.name),
            className
        )
    );
    const summary = $derived(summarizeApply({ className, selectedCount, selectionClassCounts }));
    const canApply = $derived(className.length > 0 && selectedSource.length > 0 && !isApplying);
    // The target source stays on the action itself: there is no undo for this anywhere.
    const applyLabel = $derived(
        selectedSource ? `Add annotation class to ${selectedSource}` : 'Add annotation class'
    );
</script>

{#if selectedCount > 0}
    <Segment title={`Selected images: ${selectedCount}`}>
        <div class="flex flex-col gap-3" data-testid="bulk-annotation-class-panel">
            <p class="text-sm text-muted-foreground">
                Add one annotation class to every selected image. Existing annotations are kept —
                change or remove them in the annotation view.
            </p>

            <div class="space-y-1">
                <p class="text-xs font-medium">Annotation source</p>
                <NamePicker
                    value={selectedSource}
                    options={sourceOptions}
                    placeholder="Select an annotation source"
                    searchPlaceholder="Search or create a source…"
                    ariaLabel="Annotation source"
                    onPick={onSourceChange}
                    disabled={isApplying}
                    testId="bulk-source-picker"
                />
            </div>

            <div class="space-y-1">
                <p class="text-xs font-medium">Annotation class</p>
                <NamePicker
                    value={className}
                    options={classOptions}
                    placeholder="Select an annotation class"
                    searchPlaceholder="Search or create a class…"
                    ariaLabel="Annotation class"
                    onPick={(name) => (className = name)}
                    disabled={isApplying}
                    testId="bulk-class-picker"
                />
            </div>

            <ExistingClassCounts
                source={selectedSource}
                counts={selectionClassCounts}
                isLoading={isLoadingCounts}
            />

            <Button
                variant="default"
                isPending={isApplying}
                buttonProps={{
                    type: 'button',
                    disabled: !canApply,
                    class: 'w-full min-w-0',
                    onclick: () => (isConfirming = true),
                    'data-testid': 'bulk-annotation-class-apply'
                }}
            >
                <span class="min-w-0 truncate">{applyLabel}</span>
            </Button>
        </div>
    </Segment>

    <ConfirmApplyDialog
        open={isConfirming}
        {className}
        source={selectedSource}
        affectedCount={summary.affectedCount}
        skippedCount={summary.skippedCount}
        {isApplying}
        onOpenChange={(open) => (isConfirming = open)}
        onConfirm={() => {
            isConfirming = false;
            onApply({ className, source: selectedSource });
        }}
    />
{/if}
