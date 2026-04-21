<!--
  Presentational search control.
  Renders text search + upload trigger UI while delegating state and actions to parent callbacks.
-->
<script lang="ts">
    import Input from '$lib/components/ui/input/input.svelte';
    import { Image as ImageIcon, Search, X } from '@lucide/svelte';
    type Props = {
        queryText: string;
        submittedQueryText: string;
        isUploading: boolean;
        dragOver: boolean;
        onKeyDown: (event: KeyboardEvent) => void;
        onPaste: (event: ClipboardEvent) => void;
        onClear: () => void;
        onUploadClick: () => void;
        onQueryTextChange: (value: string) => void;
    };

    let {
        queryText,
        submittedQueryText,
        isUploading,
        dragOver,
        onKeyDown,
        onPaste,
        onClear,
        onUploadClick,
        onQueryTextChange
    }: Props = $props();
</script>

<div class="relative">
    <Search class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground" />
    <Input
        placeholder={isUploading ? 'Uploading...' : 'Search samples by description or image'}
        class="pl-8 pr-8 {dragOver ? 'ring-2 ring-primary' : ''}"
        value={queryText}
        onkeydown={onKeyDown}
        onpaste={onPaste}
        oninput={(event) =>
            onQueryTextChange((event.currentTarget as HTMLInputElement | null)?.value ?? '')}
        disabled={isUploading}
        data-testid="text-embedding-search-input"
    />
    {#if submittedQueryText}
        <button
            class="absolute right-8 top-[50%] translate-y-[-50%] text-muted-foreground hover:text-foreground"
            onclick={onClear}
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
        disabled={isUploading}
    >
        <ImageIcon class="h-4 w-4" />
    </button>
</div>
