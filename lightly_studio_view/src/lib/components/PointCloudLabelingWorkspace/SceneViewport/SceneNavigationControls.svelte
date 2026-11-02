<script lang="ts">
    import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, RotateCcw, RotateCw } from '@lucide/svelte';
    import { type SceneNavigationAction } from '$lib/components/PointCloudViewer';
    import { useNavigationHighlight } from './useNavigationHighlight/useNavigationHighlight.svelte';

    /** Inputs and callbacks for scene navigation controls. */
    interface Props {
        /** Whether this viewport currently owns navigation input. */
        isActive: boolean;
        /** Whether navigation buttons and shortcut hints are shown. */
        showNavigationHelpers?: boolean;
        /** Identifies the viewport receiving navigation commands. */
        navigationId?: symbol;
        /** Enables perspective camera rotation actions. */
        allowRotation?: boolean;
    }

    let {
        isActive,
        showNavigationHelpers = true,
        navigationId,
        allowRotation = true
    }: Props = $props();

    const controls: {
        action: SceneNavigationAction;
        label: string;
        icon: typeof ArrowUp;
        key?: string;
    }[] = [
        { action: 'rotate-left', label: 'Rotate left (Q)', icon: RotateCcw, key: 'Q' },
        { action: 'forward', label: 'Move forward (W)', icon: ArrowUp, key: 'W' },
        { action: 'rotate-right', label: 'Rotate right (E)', icon: RotateCw, key: 'E' },
        { action: 'left', label: 'Move left (A)', icon: ArrowLeft, key: 'A' },
        { action: 'backward', label: 'Move backward (S)', icon: ArrowDown, key: 'S' },
        { action: 'right', label: 'Move right (D)', icon: ArrowRight, key: 'D' }
    ];
    const highlight = useNavigationHighlight(() => ({ isActive, navigationId, allowRotation }));
    const { input } = highlight;
    const visibleControls = $derived(
        controls.filter((control) => allowRotation || !control.action.startsWith('rotate-'))
    );
</script>

{#if showNavigationHelpers && isActive}
    <div
        class="absolute bottom-3 right-3 z-10 grid grid-cols-3 gap-1 rounded-md border bg-background/80 p-1 shadow"
    >
        {#each visibleControls as control (control.action)}
            <button
                type="button"
                class:col-start-2={!allowRotation && control.action === 'forward'}
                class:col-start-1={!allowRotation && control.action === 'left'}
                class:active={highlight.highlightedAction === control.action}
                class="relative flex size-8 items-center justify-center rounded hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                class:bg-accent={highlight.highlightedAction === control.action}
                class:text-accent-foreground={highlight.highlightedAction === control.action}
                aria-label={control.label}
                title={control.label}
                onpointerdown={(event) => {
                    if (event.button === 0) input.startHold(control.action);
                }}
                onpointerup={input.stopHold}
                onpointerleave={input.stopHold}
                onpointercancel={input.stopHold}
                onclick={() => input.click(control.action)}
            >
                <control.icon size={16} />
                {#if control.key}
                    <span class="absolute bottom-0 right-0.5 text-[9px] font-semibold leading-none">
                        {control.key}
                    </span>
                {/if}
            </button>
        {/each}
    </div>
{/if}
