<script lang="ts">
    import GridHeader from '$lib/components/GridHeader/GridHeader.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import Input from '$lib/components/ui/input/input.svelte';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { ChartNetwork, Image as ImageIcon, Search, X } from '@lucide/svelte';
    import { onDestroy } from 'svelte';
    import { toast } from 'svelte-sonner';

    const {
        collectionId,
        isAnnotations,
        isGroups,
        isSamples,
        isVideos,
        plotEnabled,
        showPlot,
        onTogglePlot,
        onHasEmbeddingsChange
    }: {
        collectionId: string;
        isAnnotations: boolean;
        isGroups: boolean;
        isSamples: boolean;
        isVideos: boolean;
        plotEnabled: boolean;
        showPlot: boolean;
        onTogglePlot: () => void;
        onHasEmbeddingsChange?: (value: boolean) => void;
    } = $props();

    const { setTextEmbedding, textEmbedding } = useGlobalStorage();
    const shouldShowHeader = $derived(isSamples || isAnnotations || isVideos || isGroups);

    const hasEmbeddingsQuery = $derived(
        useHasEmbeddings({
            collectionId,
            enabled: isSamples || isVideos
        })
    );
    const hasEmbeddings = $derived(Boolean($hasEmbeddingsQuery.data));

    $effect(() => {
        onHasEmbeddingsChange?.(hasEmbeddings);
    });

    let queryText = $state($textEmbedding ? $textEmbedding.queryText : '');
    let submittedQueryText = $state($textEmbedding ? $textEmbedding.queryText : '');
    let dragOver = $state(false);
    let activeImage = $state<string | null>(null);
    let previewUrl = $state<string | null>(null);
    let isUploading = $state(false);
    let fileInput = $state<HTMLInputElement | null>(null);

    const embedTextQuery = $derived(
        useEmbedText({
            collectionId,
            queryText: submittedQueryText,
            embeddingModelId: null
        })
    );

    const MAX_IMAGE_SIZE_MB = 50;
    const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;

    const setError = (errorMessage: string) => {
        toast.error('Error', { description: errorMessage });
    };

    onDestroy(() => {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
        }
    });

    async function onKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            submittedQueryText = queryText.trim();
        }
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault();
        dragOver = true;
    }

    function handleDragLeave(event: DragEvent) {
        event.preventDefault();
        dragOver = false;
    }

    async function handleDrop(event: DragEvent) {
        event.preventDefault();
        dragOver = false;

        if (!event.dataTransfer?.files?.length) {
            return;
        }

        const file = event.dataTransfer.files[0];
        if (file.type.startsWith('image/')) {
            await uploadImage(file);
            return;
        }

        setError('Please drop an image file.');
    }

    async function handlePaste(event: ClipboardEvent) {
        const clipboardData = event.clipboardData;
        if (!clipboardData) {
            return;
        }

        if (clipboardData.files?.length) {
            const file = clipboardData.files[0];
            if (file.type.startsWith('image/')) {
                event.preventDefault();
                await uploadImage(file);
                return;
            }
        }

        for (const item of clipboardData.items ?? []) {
            if (!item.type.startsWith('image/')) {
                continue;
            }

            const file = item.getAsFile();
            if (file) {
                event.preventDefault();
                await uploadImage(file);
                return;
            }
        }
    }

    async function handleFileSelect(event: Event) {
        const target = event.target as HTMLInputElement;
        if (target.files?.length) {
            await uploadImage(target.files[0]);
        }

        target.value = '';
    }

    async function uploadImage(file: File) {
        if (file.size > MAX_IMAGE_SIZE_BYTES) {
            setError(`Image is too large. Maximum size is ${MAX_IMAGE_SIZE_MB}MB.`);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        isUploading = true;
        try {
            const response = await fetch(
                `/api/image_embedding/from_file/for_collection/${collectionId}`,
                {
                    method: 'POST',
                    body: formData
                }
            );

            if (!response.ok) {
                throw new Error(`Error uploading image: ${response.statusText}`);
            }

            const embedding = await response.json();
            queryText = '';
            submittedQueryText = '';
            activeImage = file.name;

            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
            }
            previewUrl = URL.createObjectURL(file);

            setTextEmbedding({
                queryText: file.name,
                embedding
            });
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Failed to upload image';
            setError(message);
        } finally {
            isUploading = false;
        }
    }

    function clearSearch() {
        activeImage = null;
        queryText = '';
        submittedQueryText = '';

        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }

        setTextEmbedding(undefined);
    }

    function triggerFileInput() {
        fileInput?.click();
    }

    $effect(() => {
        if (activeImage) {
            return;
        }

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

{#if shouldShowHeader}
    <GridHeader>
        {#snippet auxControls()}
            {#if (isSamples || isVideos) && hasEmbeddings}
                <Button
                    class="flex items-center space-x-1"
                    data-testid="toggle-plot-button"
                    variant={plotEnabled && showPlot ? 'default' : 'ghost'}
                    onclick={onTogglePlot}
                >
                    <ChartNetwork class="size-4" />
                    <span>Show Embeddings</span>
                </Button>
            {/if}
        {/snippet}
        {#if (isSamples || isVideos) && hasEmbeddings}
            <div
                class="relative"
                role="region"
                aria-label="Search by image or text"
                ondragover={handleDragOver}
                ondragleave={handleDragLeave}
                ondrop={handleDrop}
            >
                <Search
                    class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground"
                />
                {#if activeImage || submittedQueryText}
                    <div
                        class="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm {dragOver
                            ? 'ring-2 ring-primary'
                            : ''}"
                    >
                        {#if activeImage}
                            <span
                                class="mr-2 flex items-center gap-2 truncate text-muted-foreground"
                            >
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
                        placeholder={isUploading
                            ? 'Uploading...'
                            : 'Search samples by description or image'}
                        class="pl-8 pr-8 {dragOver ? 'ring-2 ring-primary' : ''}"
                        bind:value={queryText}
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
        {/if}
    </GridHeader>
    <Separator class="mb-4 bg-border-hard" />
{/if}
