<script lang="ts">
    export let logs: { type: string; text: string }[] = [];
    
    import { afterUpdate } from 'svelte';

    let container: HTMLElement;

    afterUpdate(() => {
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    });
</script>

<div class="h-full w-full overflow-y-auto bg-black p-2 font-mono text-sm text-white" bind:this={container}>
    {#each logs as log}
        <div class:text-red-400={log.type === 'error'} class:text-green-400={log.type === 'result'} class:text-gray-300={log.type === 'stream'}>
            <pre class="whitespace-pre-wrap break-words">{log.text}</pre>
        </div>
    {/each}
</div>
