<script lang="ts">
    import { Eye, EyeOff } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';

    interface Props {
        isHidden: boolean;
        labelName: string;
        toggleClassVisibility: (labelName: string) => void;
    }

    let { isHidden, labelName, toggleClassVisibility }: Props = $props();
</script>

{#if isHidden}
    <Tooltip content="Show annotation class">
        <button
            type="button"
            aria-label="Show annotation class {labelName}"
            data-testid="label-visibility-toggle"
            class="flex shrink-0 items-center"
            onclick={() => toggleClassVisibility(labelName)}
        >
            <EyeOff class="size-4 text-muted-foreground" />
        </button>
    </Tooltip>
{:else}
    <Tooltip content="Hide annotation class">
        <button
            type="button"
            aria-label="Hide annotation class {labelName}"
            data-testid="label-visibility-toggle"
            class="flex shrink-0 items-center opacity-0 focus:opacity-100 group-hover:opacity-100"
            onclick={() => toggleClassVisibility(labelName)}
        >
            <Eye class="size-4" />
        </button>
    </Tooltip>
{/if}
