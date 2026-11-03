<script lang="ts">
    import TileFieldMarker from '$lib/components/TileFieldMarker/TileFieldMarker.svelte';
    import { cn } from '$lib/utils';
    import type { TileChip } from '../getTileChips';

    interface Props {
        chip: TileChip;
    }

    const { chip }: Props = $props();

    // Dark, semi-opaque chips stay legible on bright and dark images. Tags are outlined pills so
    // they never read as a class; metadata stays plain.
    const kindClass = {
        class: 'rounded font-medium',
        source: 'rounded font-medium',
        tag: 'rounded-full border border-white/70 font-medium',
        metadata: 'rounded font-normal'
    };
</script>

<span
    class={cn(
        'pointer-events-auto box-border flex h-5 min-w-0 max-w-full shrink-0 items-center gap-1 bg-black/60 px-1.5 text-xs leading-5 text-white backdrop-blur-sm',
        kindClass[chip.kind]
    )}
    title={chip.title}
    data-testid="tile-field-chip"
    data-kind={chip.kind}
>
    {#if chip.kind !== 'class'}
        <TileFieldMarker kind={chip.kind} name={chip.sourceName} />
    {/if}
    {#if chip.label}
        <span class="shrink-0 font-normal text-white/70">{chip.label}</span>
    {/if}
    {#if chip.value}
        <span class="truncate">{chip.value}</span>
    {/if}
    {#each chip.classes ?? [] as classCount (classCount.name)}
        <span class="flex min-w-0 items-center gap-1">
            <TileFieldMarker kind="class" name={classCount.name} />
            <span class="truncate">{classCount.text}</span>
        </span>
    {/each}
</span>
