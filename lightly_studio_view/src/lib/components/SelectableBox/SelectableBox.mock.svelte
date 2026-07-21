<script lang="ts">
    interface Props {
        isSelected?: boolean;
        onSelect?: () => void;
    }

    let { isSelected = false }: Props = $props();
</script>

<div data-testid="mock-selectable-box" data-selected={isSelected}></div>
