<!--
  Orchestrator component to keep collection search behavior in one place.
  It coordinates text embedding search, image upload search, and drag/paste/file input
  interactions, while delegating rendering details to `SearchInput` and `ImageSearchDisplay`.
-->
<script lang="ts">
    import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';
    import { useImageUpload, useFileDrop, useEmbedText } from '$lib/hooks';
    import { onDestroy } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { CollectionSearchInput, CollectionSearchImage } from '$lib/components';

    type Props = {
        collectionId: string;
        value: TextEmbedding | undefined;
        onChange: (embedding: TextEmbedding | undefined) => void;
    };

    let { collectionId, value, onChange }: Props = $props();

    let queryText = $state(value ? value.queryText : '');
    let submittedQueryText = $state(value ? value.queryText : '');
    let lastAppliedTextEmbeddingQuery = $state(value ? value.queryText : '');
    let fileInput = $state<HTMLInputElement | null>(null);

    const setError = (errorMessage: string) => {
        toast.error('Error', { description: errorMessage });
    };

    const { imageName, previewUrl, isUploading, upload, clear } = useImageUpload({
        collectionId,
        onError: setError,
        onSuccess: ({ fileName, embedding }) => {
            queryText = '';
            submittedQueryText = '';
            onChange({
                queryText: fileName,
                embedding
            });
        }
    });

    const { dragOver, handleDragOver, handleDragLeave, handleDrop, handlePaste, handleFileSelect } =
        useFileDrop({
            onFileAccepted: upload,
            onError: setError
        });

    onDestroy(() => {
        clear();
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

    const triggerFileInput = () => {
        fileInput?.click();
    };

    const clearSearch = () => {
        queryText = '';
        submittedQueryText = '';
        clear();
        onChange(undefined);
    };

    $effect(() => {
        const committedQuery = value?.queryText ?? '';
        if (committedQuery === lastAppliedTextEmbeddingQuery) {
            return;
        }

        lastAppliedTextEmbeddingQuery = committedQuery;

        if ($imageName) {
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
        if ($imageName) {
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
            onChange(undefined);
            return;
        }

        if ($embedTextQuery.isSuccess) {
            onChange({
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
    {#if $imageName}
        <CollectionSearchImage
            name={$imageName}
            src={$previewUrl}
            showOutline={$dragOver}
            onClear={clearSearch}
        />
    {:else}
        <CollectionSearchInput
            value={queryText}
            disabled={$isUploading}
            showOutline={$dragOver}
            inputProps={{
                placeholder: 'Search samples by description or image',
                onkeydown: onKeyDown,
                onpaste: handlePaste
            }}
            onUploadClick={triggerFileInput}
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
