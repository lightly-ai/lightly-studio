<script lang="ts">
    import LightlyLogo from '$lib/components/Logo/LightlyLogo.png';
    import { formatInteger } from '$lib/utils';
    import { ChevronsUpDown } from '@lucide/svelte';

    interface Props {
        datasetName: string;
        sampleCount: number | undefined;
        /** Where the mark links to — the dataset list, or home when signed out. */
        href: string;
    }

    const { datasetName, sampleCount, href }: Props = $props();
</script>

<a
    {href}
    data-testid="dataset-switcher"
    title={datasetName}
    class="mx-1.5 mt-1.5 flex h-[52px] items-center gap-[9px] rounded-[7px] pl-3 pr-2.5 transition-colors hover:bg-sidebar-accent/60"
>
    <img src={LightlyLogo} alt="LightlyStudio" class="h-[18px] shrink-0" />
    <span class="flex min-w-0 flex-1 flex-col">
        <span class="truncate text-[12.5px] font-semibold text-foreground">{datasetName}</span>
        {#if sampleCount !== undefined}
            <span class="truncate text-[11px] text-muted-foreground">
                {formatInteger(sampleCount)} samples
            </span>
        {/if}
    </span>
    <ChevronsUpDown class="size-[13px] shrink-0 text-muted-foreground" />
</a>
