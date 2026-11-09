<script lang="ts">
    import { Eye, EyeOff } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn';
    import type { TriState } from './pairRows';

    interface Props {
        eye: TriState;
        target: string;
        /** Dims the eye of a row that is filtered out. */
        dimmed?: boolean;
        onToggle: (visible: boolean) => void;
    }

    let { eye, target, dimmed = false, onToggle }: Props = $props();

    const pressed = $derived(eye === 'partial' ? 'mixed' : eye === 'on');
</script>

<button
    type="button"
    aria-label="Show {target}"
    aria-pressed={pressed}
    title={eye === 'on' ? 'Hide' : 'Show'}
    class={cn(
        'flex shrink-0 items-center rounded text-muted-foreground hover:text-foreground',
        dimmed && 'opacity-50'
    )}
    onclick={() => onToggle(eye !== 'on')}
>
    {#if eye === 'off'}
        <EyeOff class="size-4" />
    {:else}
        <Eye class={cn('size-4', eye === 'partial' && 'opacity-50')} />
    {/if}
</button>
