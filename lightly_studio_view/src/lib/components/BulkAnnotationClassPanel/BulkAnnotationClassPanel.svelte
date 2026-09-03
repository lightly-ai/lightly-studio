<script lang="ts">
    import { Info as InfoIcon } from '@lucide/svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Button } from '$lib/components';
    import * as Alert from '$lib/components/ui/alert/index.js';
    import NamePicker from './NamePicker/NamePicker.svelte';
    import ConfirmApplyDialog from './ConfirmApplyDialog/ConfirmApplyDialog.svelte';
    import { withSelectedOption } from './BulkAnnotationClassPanel.helpers';

    interface AnnotationClassOption {
        id: string;
        name: string;
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
        isApplying: boolean;
        onSourceChange: (source: string) => void;
        onApply: (args: { className: string; source: string }) => void;
    }

    const {
        selectedCount,
        annotationClasses,
        annotationSources,
        selectedSource,
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
    const canApply = $derived(className.length > 0 && selectedSource.length > 0 && !isApplying);
    const title = $derived(`${selectedCount} ${selectedCount === 1 ? 'image' : 'images'} selected`);
</script>

{#if selectedCount > 0}
    <Segment {title}>
        <div class="flex flex-col gap-3" data-testid="bulk-annotation-class-panel">
            <div class="space-y-1">
                <p class="text-xs font-medium">Source</p>
                <NamePicker
                    value={selectedSource}
                    options={sourceOptions}
                    placeholder="Select a source"
                    searchPlaceholder="Search or create…"
                    ariaLabel="Source"
                    onPick={onSourceChange}
                    disabled={isApplying}
                    testId="bulk-source-picker"
                />
            </div>

            <div class="space-y-1">
                <p class="text-xs font-medium">Class</p>
                <NamePicker
                    value={className}
                    options={classOptions}
                    placeholder="Select a class"
                    searchPlaceholder="Search or create…"
                    ariaLabel="Class"
                    onPick={(name) => (className = name)}
                    disabled={isApplying}
                    testId="bulk-class-picker"
                />
            </div>

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
                <span class="min-w-0 truncate">Add class</span>
            </Button>

            <Alert.Root
                class="flex items-start gap-2 border-border bg-muted/50 p-2 text-xs text-muted-foreground"
                data-testid="bulk-annotation-class-hint"
            >
                <InfoIcon class="mt-0.5 size-3.5 shrink-0" />
                <span>Change or remove annotations in the annotation view.</span>
            </Alert.Root>
        </div>
    </Segment>

    <ConfirmApplyDialog
        open={isConfirming}
        {className}
        source={selectedSource}
        imageCount={selectedCount}
        {isApplying}
        onOpenChange={(open) => (isConfirming = open)}
        onConfirm={() => {
            isConfirming = false;
            onApply({ className, source: selectedSource });
        }}
    />
{/if}
