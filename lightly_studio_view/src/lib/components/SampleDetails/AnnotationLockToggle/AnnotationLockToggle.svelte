<script lang="ts">
    import Lock from '@lucide/svelte/icons/lock';
    import Unlock from '@lucide/svelte/icons/unlock';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import type { LockScope } from '$lib/utils';

    interface Props {
        /** Whether every lockable annotation in the scope is locked. */
        locked: boolean;
        /** 'all' covers every source of the sample, 'source' one source group. */
        scope: Exclude<LockScope, 'annotation'>;
        onToggle: () => void;
    }

    let { locked, scope, onToggle }: Props = $props();

    const target = $derived(
        scope === 'source' ? 'all annotations in this source' : 'all annotations'
    );
    const label = $derived(locked ? `Unlock ${target}` : `Lock ${target}`);
</script>

<Tooltip content={label} noTriggerRole>
    <button
        type="button"
        aria-label={label}
        class="flex items-center"
        onclick={(e) => {
            e.stopPropagation();
            onToggle();
        }}
    >
        {#if locked}
            <Lock class="size-4 text-primary" />
        {:else}
            <Unlock class="size-4" />
        {/if}
    </button>
</Tooltip>
