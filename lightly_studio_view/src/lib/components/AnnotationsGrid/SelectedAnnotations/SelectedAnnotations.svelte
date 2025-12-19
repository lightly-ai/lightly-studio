<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import { Segment } from '$lib/components';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';

    type Props = {
        selectedAnnotations: Array<AnnotationView>;
        onSelect: (item: { value: string; label: string }) => void;
        disabled?: boolean;
        isLoading?: boolean;
        collectionId: string;
    };

    const { selectedAnnotations, onSelect, disabled, isLoading, collectionId }: Props = $props();

    const result = useAnnotationLabels({ collectionId });

    const items = $derived(getSelectionItems($result.data || []));
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <Segment title={`Selected annotations: ${selectedAnnotations.length}`}>
                <div class="flex flex-col space-y-4">
                    <div class="text-md mb-2">
                        You can edit labels for multiple annotations at once.
                    </div>
                    <SelectList
                        {items}
                        name="annotation-label"
                        placeholder="Select or create a label"
                        label="Select a label"
                        {onSelect}
                        {isLoading}
                        {disabled}
                    >
                        {#snippet notFound({ inputValue })}
                            <LabelNotFound label={inputValue} />
                        {/snippet}
                    </SelectList>
                </div>
            </Segment>
        </div>
    </CardContent>
</Card>
