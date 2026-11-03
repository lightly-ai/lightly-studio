<script lang="ts">
    import { ChevronDown, Database } from '@lucide/svelte';
    import { AnnotationSourcePicker } from '$lib/components/AnnotationSourcePicker';
    import { useColorPicker } from '$lib/hooks';

    interface Props {
        collectionId: string;
        /** The source new classifications go to, or null when the user must choose one. */
        sourceName: string | null;
        disabled: boolean;
        onPick: (sourceName: string) => Promise<boolean>;
    }
    let { collectionId, sourceName, disabled, onPick }: Props = $props();

    const picker = useColorPicker(() => sourceName ?? '');
</script>

<div class="flex items-center gap-1 border-b px-2 py-1.5 text-sm">
    <span class="text-muted-foreground">Add to</span>
    <AnnotationSourcePicker
        {collectionId}
        label="Annotation source"
        heading="Add classifications to"
        icon={Database}
        {disabled}
        {onPick}
    >
        {#snippet trigger()}
            {#if sourceName}
                <Database class="size-4" style="color: {picker.borderColor}" aria-hidden="true" />
                <span class="max-w-40 truncate font-medium">{sourceName}</span>
            {:else}
                <span class="font-semibold text-primary">Choose source</span>
            {/if}
            <ChevronDown class="size-3.5 text-muted-foreground" />
        {/snippet}
    </AnnotationSourcePicker>
</div>
