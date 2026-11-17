<script lang="ts">
    import {
        AnnotationTargetRadio,
        NewAnnotationSourceInput
    } from '$lib/components/AnnotationSource';

    interface SourceChoice {
        name: string;
        /** Whether the source is created with the cuboid. */
        isNew: boolean;
    }

    interface Props {
        /** The names of the existing annotation sources. */
        sourceNames: string[];
        selected: SourceChoice | null;
        onSelect: (choice: SourceChoice) => void;
    }

    let { sourceNames, selected, onSelect }: Props = $props();

    const shownNames = $derived(
        selected?.isNew && !sourceNames.includes(selected.name)
            ? [...sourceNames, selected.name]
            : sourceNames
    );
    const selectedNew = $derived(selected?.isNew ? selected.name : null);

    function selectTyped(name: string) {
        onSelect({ name, isNew: !sourceNames.includes(name) });
    }
</script>

<div class="space-y-1" data-testid="cuboid-source-section">
    <p class="text-sm font-medium">Annotation source</p>
    {#each shownNames as name (name)}
        <div class="flex items-center gap-2 py-0.5 text-sm">
            <AnnotationTargetRadio
                sourceName={name}
                isTarget={selected?.name === name}
                needsPick={!selected}
                onSetTarget={() => onSelect({ name, isNew: name === selectedNew })}
            />
            <span class="truncate">{name}</span>
        </div>
    {/each}
    <NewAnnotationSourceInput existingNames={sourceNames} onSubmit={selectTyped} />
</div>
