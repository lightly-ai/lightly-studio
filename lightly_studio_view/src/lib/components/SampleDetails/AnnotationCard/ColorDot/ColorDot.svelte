<script lang="ts">
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors';
    import { getColorByLabel, getColorBySource } from '$lib/utils';

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
    // The helpers read the stores once. Reading them here redraws the dot on a color change.
    const color = $derived.by(() => {
        void $customLabelColorsStore;
        void $customSourceColorsStore;
        return kind === 'source' ? getColorBySource(label).color : getColorByLabel(label).color;
    });
</script>

<span class="size-2 shrink-0 rounded-full" style:background-color={color} data-testid={testId}
></span>
