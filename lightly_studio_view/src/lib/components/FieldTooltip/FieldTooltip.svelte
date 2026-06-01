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
    const tooltipId = `field-tooltip-${Math.random().toString(36).slice(2)}`;

    $effect(() => {
        if (!visible || !wrapperEl || !tooltipEl) {
            tooltipStyle = 'visibility: hidden';
            return;
        }

        const r = wrapperEl.getBoundingClientRect();
        const t = tooltipEl.getBoundingClientRect();
        const vw = window.innerWidth;

        const vh = window.innerHeight;
        const margin = 6;
        const preferredTop = r.top - t.height - margin;
        const preferredBelow = r.bottom + margin;
        const rawTop = preferredBelow + t.height + margin <= vh ? preferredBelow : preferredTop;
        const top = Math.max(margin, Math.min(rawTop, vh - t.height - margin));
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
    onkeydown={(e) => {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
            e.preventDefault();
            visible = !visible;
        }
    }}
    tabindex="0"
    role="button"
    aria-label="More information"
    aria-expanded={visible}
    aria-describedby={visible ? tooltipId : undefined}
>
    <CircleHelp class="size-3 text-muted-foreground" aria-hidden="true" />
    {#if visible}
        <div
            bind:this={tooltipEl}
            style={tooltipStyle}
            class="fixed z-50 w-max max-w-[220px] rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md"
            id={tooltipId}
            role="tooltip"
        >
            {content}
        </div>
    {/if}
</div>
