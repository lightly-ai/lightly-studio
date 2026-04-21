<!--
  Orchestrator component to keep collection search behavior in one place.
  It coordinates text embedding search, image upload search, and drag/paste/file input
  interactions, while delegating rendering details to `SearchInput` and `ImageSearchDisplay`.
-->
<script lang="ts">
    import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';
    import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';
    import { useFileDrop } from '$lib/hooks/useFileDrop';
    import { useImageUpload } from '$lib/hooks/useImageUpload';
    import { onDestroy } from 'svelte';
    import { toast } from 'svelte-sonner';
    import SearchInput from './SearchInput/SearchInput.svelte';
    import ImageSearchDisplay from './ImageSearchDisplay/ImageSearchDisplay.svelte';

    type Props = {
        collectionId: string;
        textEmbedding: TextEmbedding | undefined;
        setTextEmbedding: (embedding: TextEmbedding | undefined) => void;
    };

    let { collectionId, textEmbedding, setTextEmbedding }: Props = $props();

    let queryText = $state(textEmbedding ? textEmbedding.queryText : '');
    let submittedQueryText = $state(textEmbedding ? textEmbedding.queryText : '');
    let lastAppliedTextEmbeddingQuery = $state(textEmbedding ? textEmbedding.queryText : '');
    let fileInput = $state<HTMLInputElement | null>(null);

    const setError = (errorMessage: string) => {
        toast.error('Error', { description: errorMessage });
    };

    const { activeImage, previewUrl, isUploading, uploadImage, clearImage } = useImageUpload({
        collectionId,
        onError: setError,
        onUploadSuccess: ({ fileName, embedding }) => {
            queryText = '';
            submittedQueryText = '';
            setTextEmbedding({
                queryText: fileName,
                embedding
            });
        }
    });

    const { dragOver, handleDragOver, handleDragLeave, handleDrop, handlePaste, handleFileSelect } =
        useFileDrop({
            onFile: uploadImage,
            onError: setError
        });

    onDestroy(() => {
        clearImage();
    });

    const embedTextQuery = $derived(
        useEmbedText({
            collectionId,
            queryText: submittedQueryText,
            embeddingModelId: null
        })
    );

    async function onKeyDown(event: KeyboardEvent) {
        const input = event.currentTarget as HTMLInputElement | null;

        if (event.key === 'Enter') {
            event.preventDefault();
            const trimmedQuery = queryText.trim();
            if (!trimmedQuery) {
                clearSearch();
                input?.blur();
                return;
            }

            queryText = trimmedQuery;
            submittedQueryText = trimmedQuery;
            input?.blur();
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            if (submittedQueryText) {
                queryText = submittedQueryText;
            } else {
                queryText = '';
            }
            input?.blur();
        }
    }

    const onQueryTextChange = (value: string) => {
        queryText = value;
    };

    const triggerFileInput = () => {
        fileInput?.click();
    };

    const clearSearch = () => {
        queryText = '';
        submittedQueryText = '';
        clearImage();
        setTextEmbedding(undefined);
    };

    $effect(() => {
        const committedQuery = textEmbedding?.queryText ?? '';
        if (committedQuery === lastAppliedTextEmbeddingQuery) {
            return;
        }

        lastAppliedTextEmbeddingQuery = committedQuery;

        if ($activeImage) {
            return;
        }

        if (!committedQuery) {
            submittedQueryText = '';
            queryText = '';
            return;
        }

        submittedQueryText = committedQuery;
        queryText = committedQuery;
    });

    $effect(() => {
        if ($activeImage) {
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

<div
    class="relative"
    role="region"
    aria-label="Search by image or text"
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    ondrop={handleDrop}
>
    {#if $activeImage}
        <ImageSearchDisplay
            activeImage={$activeImage}
            previewUrl={$previewUrl}
            dragOver={$dragOver}
            onClear={clearSearch}
        />
    {:else}
        <SearchInput
            {queryText}
            {submittedQueryText}
            isUploading={$isUploading}
            dragOver={$dragOver}
            {onKeyDown}
            onPaste={handlePaste}
            onClear={clearSearch}
            onUploadClick={triggerFileInput}
            {onQueryTextChange}
        />
    {/if}

    <input
        type="file"
        accept="image/*"
        class="hidden"
        bind:this={fileInput}
        onchange={handleFileSelect}
        disabled={$isUploading}
    />
</div>
