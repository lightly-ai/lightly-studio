<script lang="ts">
    import { AnnotationTargetRadio } from '$lib/components/AnnotationSource';
    import { Input } from '$lib/components/ui/input';

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

    // Typing selects the source at once, so the name is kept also when the user clicks Confirm
    // without Enter.
    function selectTyped(value: string) {
        const name = value.trim();
        if (name) onSelect({ name, isNew: !sourceNames.includes(name) });
    }
</script>

<div class="space-y-1" data-testid="cuboid-source-section">
    <p class="text-sm font-medium">Annotation source</p>
    <p class="text-xs text-muted-foreground" data-testid="cuboid-source-hint">
        A group of annotations, for example manual annotations or the predictions of a model. This
        is not the annotation class.
    </p>
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
    <Input
        class="h-8 px-2 text-sm"
        placeholder="New source, for example manual annotations"
        aria-label="New annotation source name"
        oninput={(event) => selectTyped(event.currentTarget.value)}
        onkeydown={(event) => event.key === 'Enter' && event.preventDefault()}
        data-testid="cuboid-new-source-input"
    />
</div>
