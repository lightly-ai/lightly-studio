<script lang="ts">
    import { Search, Image as ImageIcon, X } from '@lucide/svelte';
    import Input from '$lib/components/ui/input/input.svelte';

    interface Props {
        queryText: string;
        submittedQueryText: string;
        activeImage: string | null;
        previewUrl: string | null;
        isUploading?: boolean;
        isDragOver?: boolean;
        onQueryTextInput: (value: string) => void;
        onKeyDown: (event: KeyboardEvent) => void;
        onPaste: (event: ClipboardEvent) => void;
        onDragOver: (event: DragEvent) => void;
        onDragLeave: (event: DragEvent) => void;
        onDrop: (event: DragEvent) => void;
        onClearSearch: () => void;
        onFileSelect: (event: Event) => void;
    }

    let {
        queryText,
        submittedQueryText,
        activeImage,
        previewUrl,
        isUploading = false,
        isDragOver = false,
        onQueryTextInput,
        onKeyDown,
        onPaste,
        onDragOver,
        onDragLeave,
        onDrop,
        onClearSearch,
        onFileSelect
    }: Props = $props();

    let fileInput = $state<HTMLInputElement | null>(null);

    function triggerFileInput() {
        fileInput?.click();
    }
</script>

<div
    class="relative"
    role="region"
    aria-label="Search by image or text"
    ondragover={onDragOver}
    ondragleave={onDragLeave}
    ondrop={onDrop}
>
    <Search class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground" />
    {#if activeImage}
        <div
            class="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm {isDragOver
                ? 'ring-2 ring-primary'
                : ''}"
        >
            <span class="mr-2 flex items-center gap-2 truncate text-muted-foreground">
                {#if previewUrl}
                    <img
                        src={previewUrl}
                        alt="Search preview"
                        class="h-6 w-6 rounded object-cover"
                    />
                {:else}
                    <ImageIcon class="h-4 w-4" />
                {/if}
                {activeImage}
            </span>
            <button
                class="ml-auto hover:text-foreground"
                onclick={onClearSearch}
                title="Clear search"
                data-testid="search-clear-button"
            >
                <X class="h-4 w-4" />
            </button>
        </div>
    {:else}
        <Input
            placeholder={isUploading ? 'Uploading...' : 'Search samples by description or image'}
            class="pl-8 pr-8 {isDragOver ? 'ring-2 ring-primary' : ''}"
            value={queryText}
            oninput={(e) => onQueryTextInput((e.target as HTMLInputElement).value)}
            onkeydown={onKeyDown}
            onpaste={onPaste}
            disabled={isUploading}
            data-testid="text-embedding-search-input"
        />
        {#if submittedQueryText}
            <button
                class="absolute right-8 top-[50%] translate-y-[-50%] text-muted-foreground hover:text-foreground"
                onclick={onClearSearch}
                title="Clear search"
                data-testid="search-clear-button"
            >
                <X class="h-4 w-4" />
            </button>
        {/if}
        <button
            class="absolute right-2 top-[50%] translate-y-[-50%] text-muted-foreground hover:text-foreground disabled:opacity-50"
            onclick={triggerFileInput}
            title="Upload image for search"
            disabled={isUploading}
        >
            <ImageIcon class="h-4 w-4" />
        </button>
    {/if}
    <input
        type="file"
        accept="image/*"
        class="hidden"
        bind:this={fileInput}
        onchange={onFileSelect}
        disabled={isUploading}
    />
</div>
