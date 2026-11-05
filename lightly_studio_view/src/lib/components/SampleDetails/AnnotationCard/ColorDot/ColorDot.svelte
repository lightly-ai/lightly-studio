<script lang="ts">
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors';
    import { getDefaultColor, getLabelColor } from '$lib/utils';

    // The color of a class or annotation source, as the canvas draws it.
    interface Props {
        label: string;
        /** Classes and sources keep their custom colors apart. */
        kind?: 'class' | 'source';
        testId?: string;
    }

    const { label, kind = 'class', testId }: Props = $props();
    const { customLabelColorsStore } = useCustomLabelColors();
    const { customSourceColorsStore } = useCustomSourceColors();
    const color = $derived(
        kind === 'source'
            ? ($customSourceColorsStore[label]?.color ?? getDefaultColor(label, 1).color)
            : getLabelColor($customLabelColorsStore, label)
    );
</script>

<span class="size-2 shrink-0 rounded-full" style:background-color={color} data-testid={testId}
></span>
