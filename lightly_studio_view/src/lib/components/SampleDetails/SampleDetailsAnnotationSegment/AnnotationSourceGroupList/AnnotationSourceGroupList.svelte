<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleDetailsAnnotationSourceGroup } from '$lib/components';
    import type { Snippet } from 'svelte';
    import { AnnotationTargetHint } from '$lib/components/SampleDetails/AnnotationTargetHint';
    import { AnnotationTargetRadio } from '$lib/components/SampleDetails/AnnotationTargetRadio';
    import type { useAnnotationPanelVisibility } from '../useAnnotationPanelVisibility.svelte';

    type Visibility = ReturnType<typeof useAnnotationPanelVisibility>;

    // The annotations of a sample, one group per annotation source.
    interface Props {
        groups: { id: string; name: string; annotations: AnnotationView[] }[];
        sampleId: string;
        /** The source new annotations go to, or null when none is picked. */
        targetSource: string | null;
        /** Whether the user can pick the target source here. */
        canPickTarget: boolean;
        onSetTarget: (sourceName: string) => void;
        visibility: Pick<
            Visibility,
            'isGroupHidden' | 'isGroupInitiallyOpen' | 'setGroupOpen' | 'toggleGroup'
        >;
        colorBySource: boolean;
        row: Snippet<[AnnotationView]>;
    }

    let {
        groups,
        sampleId,
        targetSource,
        canPickTarget,
        onSetTarget,
        visibility,
        colorBySource,
        row
    }: Props = $props();
</script>

{#if canPickTarget}
    <AnnotationTargetHint needsPick={targetSource === null} />
{/if}
<div class="flex flex-col gap-3">
    {#each groups as group (group.id)}
        {@const isTarget = group.name === targetSource}
        {@const isHidden = visibility.isGroupHidden(group)}
        <SampleDetailsAnnotationSourceGroup
            name={group.name}
            count={group.annotations.length}
            {sampleId}
            initiallyOpen={visibility.isGroupInitiallyOpen(group)}
            showColorMarker={colorBySource}
            highlighted={isTarget && canPickTarget}
            subtitle={isTarget && canPickTarget ? 'New annotations go here' : undefined}
            allHidden={isHidden}
            onToggleVisibility={group.annotations.length > 0
                ? (e) => {
                      e.stopPropagation();
                      visibility.toggleGroup(group);
                  }
                : undefined}
            onOpenChange={(open) => visibility.setGroupOpen(group.id, open)}
        >
            {#snippet leading()}
                {#if canPickTarget}
                    <AnnotationTargetRadio
                        sourceName={group.name}
                        {isTarget}
                        isSourceHidden={isHidden}
                        needsPick={targetSource === null}
                        onSetTarget={() => onSetTarget(group.name)}
                    />
                {/if}
            {/snippet}
            {#if group.annotations.length === 0}
                <p class="text-sm text-muted-foreground">No annotations on this sample.</p>
            {:else}
                <div class="flex flex-col gap-2">
                    {#each group.annotations as annotation (annotation.sample_id)}
                        {@render row(annotation)}
                    {/each}
                </div>
            {/if}
        </SampleDetailsAnnotationSourceGroup>
    {/each}
</div>
