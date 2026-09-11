<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import ConfirmApplyDialog from './ConfirmApplyDialog/ConfirmApplyDialog.svelte';
    import NamePickerField from './NamePickerField/NamePickerField.svelte';

    interface Props {
        selectedCount: number;
        sourceName?: string;
        className?: string;
        sourceNames: string[];
        classNames: string[];
        isApplying?: boolean;
        onSourceSelect: (name: string) => void;
        onClassSelect: (name: string) => void;
        onApply: () => Promise<void> | void;
    }

    let {
        selectedCount,
        sourceName,
        className,
        sourceNames,
        classNames,
        isApplying = false,
        onSourceSelect,
        onClassSelect,
        onApply
    }: Props = $props();

    const canApply = $derived(Boolean(sourceName && className) && selectedCount > 0 && !isApplying);
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <Segment title={`Selected images: ${selectedCount}`}>
                <div class="flex flex-col space-y-4">
                    <NamePickerField
                        label="Annotation source"
                        placeholder="Select an annotation source"
                        selectedName={sourceName}
                        names={sourceNames}
                        disabled={isApplying}
                        onSelect={onSourceSelect}
                    />
                    <NamePickerField
                        label="Annotation class"
                        placeholder="Select an annotation class"
                        selectedName={className}
                        names={classNames}
                        disabled={isApplying}
                        onSelect={onClassSelect}
                    />
                    <ConfirmApplyDialog
                        {selectedCount}
                        {sourceName}
                        {className}
                        {canApply}
                        {isApplying}
                        {onApply}
                    />
                </div>
            </Segment>
        </div>
    </CardContent>
</Card>
