<script lang="ts">
    import type { Snippet } from 'svelte';
    import { NewAnnotationSourceInput } from '$lib/components/AnnotationSource';
    import type { SourcePicker } from '../pointCloudAnnotationList';

    interface Props {
        picker: SourcePicker;
        /** The names of the existing annotation sources. */
        sourceNames: string[];
        /** The source groups, each with a radio. */
        children: Snippet;
    }

    let { picker, sourceNames, children }: Props = $props();

    function pickTypedSource(name: string): void {
        if (sourceNames.includes(name)) picker.onPick(name);
        else picker.onPick(name, { isNew: true });
    }
</script>

{#if picker.needsPick}
    <p class="mb-2 text-xs text-amber-500">Pick where new annotations go.</p>
{/if}
{@render children()}
<NewAnnotationSourceInput existingNames={sourceNames} onSubmit={pickTypedSource} />
