<script lang="ts">
    interface Props {
        urls: string[];
    }
    let { urls }: Props = $props();
</script>

{#if urls.length > 0}
    <span class="flex shrink-0 items-center" data-testid="selection-thumbnails">
        {#each urls as url, index (url)}
            <img
                src={url}
                alt=""
                class="size-5 shrink-0 rounded border-2 border-card object-cover shadow-sm {index >
                0
                    ? '-ml-2'
                    : ''}"
                style:z-index={urls.length - index}
                loading="lazy"
            />
        {/each}
    </span>
{/if}
