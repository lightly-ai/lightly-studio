<script lang="ts">
    import { Search, Image as ImageIcon, X } from '@lucide/svelte';
    import Input from '$lib/components/ui/input/input.svelte';
    import { page } from '$app/state';
    import { toast } from 'svelte-sonner';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';

    const { textEmbedding, setTextEmbedding } = useGlobalStorage();

    const MAX_IMAGE_SIZE_MB = 50;
    const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;

    let dragOver = $state(false);
    let activeImage = $state<string | null>(null);
    let submittedQueryText = $state('');
    let previewUrl = $state<string | null>(null);
    let isUploading = $state(false);
    let query_text = $state($textEmbedding ? $textEmbedding.queryText : '');
    let fileInput = $state<HTMLInputElement | null>(null);

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        dragOver = true;
    }

    function handleDragLeave(e: DragEvent) {
        e.preventDefault();
        dragOver = false;
    }

    const setError = (errorMessage: string) => {
        toast.error('Error', { description: errorMessage });
    };

    async function uploadImage(file: File) {
        if (file.size > MAX_IMAGE_SIZE_BYTES) {
            setError(`Image is too large. Maximum size is ${MAX_IMAGE_SIZE_MB}MB.`);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        isUploading = true;
        try {
            const currentCollectionId = page.params.collection_id;
            if (!currentCollectionId) {
                throw new Error('Collection ID is not available');
            }
            const response = await fetch(
                `/api/image_embedding/from_file/for_collection/${currentCollectionId}`,
                {
                    method: 'POST',
                    body: formData
                }
            );

            if (!response.ok) {
                throw new Error(`Error uploading image: ${response.statusText}`);
            }

            const embedding = await response.json();

            // Clear text search state
            query_text = '';
            submittedQueryText = '';
            activeImage = file.name;

            // Create preview URL for the uploaded image
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
            }
            previewUrl = URL.createObjectURL(file);

            setTextEmbedding({
                queryText: file.name,
                embedding: embedding
            });
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to upload image';
            setError(message);
        } finally {
            isUploading = false;
        }
    }

    async function handleDrop(e: DragEvent) {
        e.preventDefault();
        dragOver = false;
        if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                await uploadImage(file);
            } else {
                setError('Please drop an image file.');
            }
        }
    }

    async function onKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            const trimmedQuery = query_text.trim();
            submittedQueryText = trimmedQuery;
        }
    }

    function clearSearch() {
        activeImage = null;
        query_text = '';
        submittedQueryText = '';
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
        setTextEmbedding(undefined);
    }

    async function handlePaste(e: ClipboardEvent) {
        const clipboardData = e.clipboardData;
        if (!clipboardData) return;

        // Check clipboardData.files first (most common case)
        if (clipboardData.files && clipboardData.files.length > 0) {
            const file = clipboardData.files[0];
            if (file.type.startsWith('image/')) {
                e.preventDefault();
                await uploadImage(file);
                return;
            }
        }

        // Fallback: check clipboardData.items (screenshots, images copied from web)
        const items = clipboardData.items;
        if (items) {
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    if (file) {
                        e.preventDefault();
                        await uploadImage(file);
                        return;
                    }
                }
            }
        }
    }

    function triggerFileInput() {
        fileInput?.click();
    }

    async function handleFileSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files && target.files.length > 0) {
            await uploadImage(target.files[0]);
        }
        // Reset input
        target.value = '';
    }
    const collectionId = $derived(page.params.collection_id!);

    const embedTextQuery = $derived(
        useEmbedText({
            collectionId,
            queryText: submittedQueryText,
            embeddingModelId: null
        })
    );

    $effect(() => {
        if (activeImage) return;

        if ($embedTextQuery.isError && $embedTextQuery.error) {
            const queryError = $embedTextQuery.error as
                | { error?: unknown; message?: string }
                | Error;
            const message = 'error' in queryError ? queryError.error : queryError.message;
            setError(String(message));
            return;
        }

        if (!submittedQueryText) {
            setTextEmbedding(undefined);
            return;
        }

        if ($embedTextQuery.isSuccess) {
            setTextEmbedding({
                queryText: submittedQueryText,
                embedding: $embedTextQuery.data
            });
        }
    });
</script>

<div
    class="relative"
    role="region"
    aria-label="Search by image or text"
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    ondrop={handleDrop}
>
    <Search class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground" />
    {#if activeImage || submittedQueryText}
        <div
            class="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm {dragOver
                ? 'ring-2 ring-primary'
                : ''}"
        >
            {#if activeImage}
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
            {:else}
                <button
                    type="button"
                    class="mr-2 min-w-0 flex-1 cursor-text truncate text-left text-muted-foreground"
                    onclick={() => {
                        submittedQueryText = '';
                    }}
                >
                    {submittedQueryText}
                </button>
            {/if}
            <button
                class="ml-auto hover:text-foreground"
                onclick={clearSearch}
                title="Clear search"
                data-testid="search-clear-button"
            >
                <X class="h-4 w-4" />
            </button>
        </div>
    {:else}
        <Input
            placeholder={isUploading ? 'Uploading...' : 'Search samples by description or image'}
            class="pl-8 pr-8 {dragOver ? 'ring-2 ring-primary' : ''}"
            bind:value={query_text}
            onkeydown={onKeyDown}
            onpaste={handlePaste}
            disabled={isUploading}
            data-testid="text-embedding-search-input"
        />
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
        onchange={handleFileSelect}
        disabled={isUploading}
    />
</div>
