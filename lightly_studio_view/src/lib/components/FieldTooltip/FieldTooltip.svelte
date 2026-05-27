<script lang="ts">
    import { CircleHelp } from '@lucide/svelte';

    interface Props {
        content: string;
    }

    let { content }: Props = $props();
    let visible = $state(false);
    let wrapperEl: HTMLDivElement | undefined = $state();
    let tooltipEl: HTMLDivElement | undefined = $state();
    let tooltipStyle = $state('visibility: hidden');

    $effect(() => {
        if (!visible || !wrapperEl || !tooltipEl) {
            tooltipStyle = 'visibility: hidden';
            return;
        }

        const r = wrapperEl.getBoundingClientRect();
        const t = tooltipEl.getBoundingClientRect();
        const vw = window.innerWidth;

        const top = r.top - t.height - 6 >= 0 ? r.top - t.height - 6 : r.bottom + 6;
        const left = Math.max(8, Math.min(r.left + r.width / 2 - t.width / 2, vw - t.width - 8));

        tooltipStyle = `top: ${top}px; left: ${left}px;`;
    });
</script>

<div
    bind:this={wrapperEl}
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
            bind:this={tooltipEl}
            style={tooltipStyle}
            class="fixed z-50 w-max max-w-[220px] rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md"
            role="tooltip"
        >
            {content}
        </div>
    {/if}
</div>
