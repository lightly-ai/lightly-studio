<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';

    const {
        isSelected = false,
        onSelect
    }: {
        /**
         * Whether the box is currently selected
         * @default false
         */
        isSelected?: boolean;

        /**
         * Callback fired when selection state changes
         */
        onSelect: (selected: boolean) => void;
    } = $props();
</script>

<Checkbox checked={isSelected} onCheckedChange={onSelect} data-testid="sample-selected-box" />
