<script lang="ts">
    import { Database } from '@lucide/svelte';
    import { ColorPicker } from '$lib/components/ui/color-picker';
    import { useClassColorPicker, useSourceColorPicker } from '$lib/hooks';
    import type { TreeMark } from './treeBranches';

    interface Props {
        mark: TreeMark;
        colorMode: 'class' | 'source';
    }

    let { mark, colorMode }: Props = $props();

    const classPicker = useClassColorPicker(() => mark.name);
    const sourcePicker = useSourceColorPicker(() => mark.name);
    const isTintedSource = $derived(mark.kind === 'source' && colorMode === 'source');
</script>

{#if mark.kind === 'class'}
    {#if colorMode === 'class'}
        <span
            class="inline-block size-2.5 shrink-0 rounded-full"
            style="background-color: {classPicker.borderColor}"
            data-testid="annotation-tree-class-dot"
        ></span>
    {/if}
{:else if isTintedSource}
    <!-- Source colors stay browser-only until Settings has an annotation sources page. -->
    <ColorPicker
        initialColor={sourcePicker.initialColor}
        initialAlpha={sourcePicker.initialAlpha}
        onChange={sourcePicker.setColor}
        onClose={sourcePicker.finishColorChange}
    >
        <span
            class="flex"
            role="img"
            aria-label="Change color of {mark.name}"
            data-testid="annotation-tree-source-icon"
            data-color={sourcePicker.borderColor}
        >
            <Database class="size-4" style="color: {sourcePicker.borderColor}" aria-hidden="true" />
        </span>
    </ColorPicker>
{:else}
    <Database
        class="size-4 shrink-0 text-muted-foreground"
        aria-hidden="true"
        data-testid="annotation-tree-source-icon"
    />
{/if}
