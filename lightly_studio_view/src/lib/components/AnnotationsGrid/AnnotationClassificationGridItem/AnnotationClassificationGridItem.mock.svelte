<script lang="ts">
    import type { ClassificationTile } from '../groupClassificationsBySample';

    interface Props {
        tile: ClassificationTile;
        selected?: boolean;
    }

    let { tile, selected = false }: Props = $props();
</script>

<div
    data-testid="mock-classification-grid-item"
    data-sample-id={tile.sampleId}
    data-selected={selected}
></div>
