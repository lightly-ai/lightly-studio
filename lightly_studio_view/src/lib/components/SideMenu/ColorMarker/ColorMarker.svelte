<script lang="ts">
    import { useColorPicker } from '$lib/hooks';
    import type { HTMLAttributes } from 'svelte/elements';
    import { ColorPicker } from '../../ui/color-picker';

    interface Props {
        label: string;
        markerProps?: HTMLAttributes<HTMLSpanElement>;
        /** When true, clicking the swatch opens a color picker. */
        enableColorPicker?: boolean;
    }

    let { label, markerProps, enableColorPicker = false }: Props = $props();

    const picker = useColorPicker(() => label);
</script>

{#if enableColorPicker}
    <ColorPicker
        initialColor={picker.initialColor}
        initialAlpha={picker.initialAlpha}
        onChange={picker.setColor}
    >
        <span
            class="inline-block h-3 w-3 shrink-0 cursor-pointer rounded-sm border"
            style="background-color: {picker.backgroundColor}; border-color: {picker.borderColor};"
            {...markerProps}
        ></span>
    </ColorPicker>
{:else}
    <span
        class="inline-block h-3 w-3 shrink-0 rounded-sm border"
        style="background-color: {picker.backgroundColor}; border-color: {picker.borderColor};"
        {...markerProps}
    ></span>
{/if}
