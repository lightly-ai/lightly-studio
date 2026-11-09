<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import type { TriState } from './pairRows';
    import TreeEye from './TreeEye.svelte';

    interface Props {
        tick: TriState;
        eye?: TriState;
        count?: string;
        onToggle: (ticked: boolean) => void;
        onToggleEye: (visible: boolean) => void;
    }

    let { tick, eye, count, onToggle, onToggleEye }: Props = $props();
</script>

<div class="flex w-full items-center gap-2 px-2 py-1.5" data-testid="annotation-tree-root">
    <Checkbox
        checked={tick === 'on'}
        indeterminate={tick === 'partial'}
        aria-label="All annotations"
        onCheckedChange={() => onToggle(tick !== 'on')}
    />
    <span class="min-w-0 flex-1 truncate text-sm font-medium">All annotations</span>
    {#if count}
        <span class="shrink-0 whitespace-nowrap text-sm text-diffuse-foreground">{count}</span>
    {/if}
    {#if eye}
        <TreeEye {eye} target="All annotations" dimmed={tick === 'off'} onToggle={onToggleEye} />
    {/if}
</div>
