<script lang="ts">
    import type { WorkspaceCrumb } from './types';

    interface Props {
        sampleId: string;
        sourcePath: WorkspaceCrumb[];
        onExit: () => void;
    }

    let { sampleId, sourcePath, onExit }: Props = $props();
</script>

<div data-testid="point-cloud-labeling-workspace" data-sample-id={sampleId}>
    <nav>
        {#each sourcePath as crumb}
            {#if crumb.href}
                <a href={crumb.href}>{crumb.label}</a>
            {:else}
                <span>{crumb.label}</span>
            {/if}
        {/each}
    </nav>
    <button onclick={onExit}>Exit</button>
</div>
