<!--
  Presentational search control.
  Renders text search + upload trigger UI while delegating state and actions to parent callbacks.
-->
<script lang="ts">
    import Input from '$lib/components/ui/input/input.svelte';
    import { cn } from '$lib/utils/shadcn';
    import { Image as ImageIcon, Search, X } from '@lucide/svelte';
    import type { HTMLInputAttributes } from 'svelte/elements';

    type CollectionSearchInputProps = Pick<
        HTMLInputAttributes,
        'placeholder' | 'disabled' | 'onkeydown' | 'onpaste'
    >;

    interface Props {
        /** Bindable current value in the search input. */
        value?: string;
        /** Input element overrides (e.g. `placeholder`, `onkeydown`) controlled by parent. */
        inputProps?: CollectionSearchInputProps;
        /** Enables focus-style outline around the input when true. */
        showOutline?: boolean;
        /** Called when the upload button is clicked. */
        onUploadClick: () => void;
        /** Disables the entire input when true. */
        disabled?: boolean;
    }

    let {
        value = $bindable(''),
        inputProps,
        disabled = false,
        showOutline = false,
        onUploadClick
    }: Props = $props();
</script>

<div class="relative">
    <Search class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground" />
    <Input
        placeholder="Search samples by description or image"
        class={cn('pl-8 pr-8', showOutline && 'ring-2 ring-primary')}
        bind:value
        data-testid="text-embedding-search-input"
        {disabled}
        {...inputProps}
    />
    {#if value}
        <button
            class="absolute right-8 top-[50%] translate-y-[-50%] text-muted-foreground hover:text-foreground"
            onclick={() => (value = '')}
            title="Clear search"
            data-testid="search-clear-button"
        >
            <X class="h-4 w-4" />
        </button>
    {/if}
    <button
        class="absolute right-2 top-[50%] translate-y-[-50%] text-muted-foreground hover:text-foreground disabled:opacity-50"
        onclick={onUploadClick}
        title="Upload image for search"
        {disabled}
    >
        <ImageIcon class="h-4 w-4" />
    </button>
</div>
