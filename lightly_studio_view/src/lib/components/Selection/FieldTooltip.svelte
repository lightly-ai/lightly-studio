<script lang="ts">
    import { CircleHelp } from '@lucide/svelte';

    interface Props {
        content: string;
    }

    let { content }: Props = $props();
    let visible = $state(false);
</script>

<div
    class="relative inline-flex items-center"
    onmouseenter={() => (visible = true)}
    onmouseleave={() => (visible = false)}
    onfocusin={() => (visible = true)}
    onfocusout={() => (visible = false)}
    tabindex="0"
    role="button"
    aria-label="More information"
>
    <CircleHelp class="size-3 text-muted-foreground" aria-hidden="true" />
    {#if visible}
        <div
            class="absolute bottom-full left-1/2 z-50 mb-1.5 w-max max-w-[220px] -translate-x-1/2 rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md"
            role="tooltip"
        >
            {content}
        </div>
    {/if}
</div>
