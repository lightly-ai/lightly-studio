<script lang="ts">
    import CuboidDraftTarget from './CuboidDraftTarget.svelte';
    import type { CuboidBox } from './cuboidDraft';

    interface Props {
        onCreateCuboid?: (box: CuboidBox) => void;
        onHighlightChange: (box: CuboidBox | null) => void;
    }
    let { onHighlightChange, onCreateCuboid }: Props = $props();
    let highlight = $state.raw<CuboidBox | null>(null);
    const layout = $derived.by(() => {
        void highlight;
        return {
            onHighlightChange: (box: CuboidBox | null) => {
                onHighlightChange(box);
                highlight = box;
            }
        };
    });
    const bounds = { min: [-4, -4, 0], max: [4, 4, 2] } as const;
</script>

{#each ['perspective', 'front', 'side', 'top'] as const as mode}
    <CuboidDraftTarget
        {bounds}
        cameraMode={mode}
        onHighlightChange={layout.onHighlightChange}
        onCreateCuboid={(box) => onCreateCuboid?.(box)}
    />
{/each}
