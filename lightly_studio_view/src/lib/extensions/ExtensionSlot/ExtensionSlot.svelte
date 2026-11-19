<script lang="ts">
    import type { Component, Snippet } from 'svelte';
    import { registry } from '$lib/extensions/registry';
    import type { SlotProps } from '$lib/extensions/slots';

    type SlotName = keyof SlotProps;

    // A union over all slots, so a call site can only pair a slot name with its own props.
    type Props = { [Name in SlotName]: { name: Name; props: SlotProps[Name] } }[SlotName] & {
        children?: Snippet;
    };

    const { name, props, children }: Props = $props();

    // The call site checked the name and props pair, so the registered components accept props.
    const components = $derived((registry[name] ?? []) as Component<Record<string, unknown>>[]);
</script>

{#if components.length > 0}
    {#each components as Item (Item)}
        <Item {...props} />
    {/each}
{:else}
    {@render children?.()}
{/if}
