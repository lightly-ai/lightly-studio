<script lang="ts">
    import { Rotate3d } from '@lucide/svelte';
    interface Props {
        target?: HTMLDivElement;
        cursorX: number;
        cursorY: number;
    }
    let { target, cursorX, cursorY }: Props = $props();
    let isRotating = $state(false);
    $effect(() => {
        if (!target) return;
        const element = target;
        const start = (event: MouseEvent) => {
            if (event.button === 0 && event.target instanceof HTMLCanvasElement) isRotating = true;
        };
        const stop = () => {
            isRotating = false;
        };
        element.addEventListener('mousedown', start);
        window.addEventListener('mouseup', stop);
        window.addEventListener('blur', stop);
        return () => {
            element.removeEventListener('mousedown', start);
            window.removeEventListener('mouseup', stop);
            window.removeEventListener('blur', stop);
        };
    });
</script>

{#if isRotating}
    <div
        class="pointer-events-none absolute z-20"
        style={`left: ${cursorX + 14}px; top: ${cursorY + 14}px`}
        aria-hidden="true"
    >
        <Rotate3d class="size-5 text-white drop-shadow" />
    </div>
{/if}
