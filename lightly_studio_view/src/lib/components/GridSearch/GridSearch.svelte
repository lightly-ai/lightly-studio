<script lang="ts">
    import { page } from '$app/state';
    import { toast } from 'svelte-sonner';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';
    import { useFileUpload } from '$lib/hooks/useFileUpload/useFileUpload';
    import { useImageUploadHandlers } from './hooks/useImageUploadHandlers/useImageUploadHandlers';
    import { embedImageFromFileMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import SearchInput from './SearchInput/SearchInput.svelte';
    import ActiveSearchDisplay from './ActiveSearchDisplay/ActiveSearchDisplay.svelte';

    const { textEmbedding, setTextEmbedding } = useGlobalStorage();
    const MAX_IMAGE_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

    let activeImage = $state<string | null>(null);
    let submittedQueryText = $state('');
    let previewUrl = $state<string | null>(null);
    let query_text = $state($textEmbedding ? $textEmbedding.queryText : '');
    let fileInput = $state<HTMLInputElement | null>(null);

    const collectionId = $derived(page.params.collection_id!);
    const showError = (message: string) => toast.error('Error', { description: message });

    const { isUploading, uploadFile } = useFileUpload({
        mutationFn: embedImageFromFileMutation,
        maxFileSize: MAX_IMAGE_SIZE_BYTES,
        acceptedTypes: ['image/'],
        buildMutationVariables: (file) => ({
            body: { file },
            path: { collection_id: collectionId }
        }),
        onSuccess: (embedding) => {
            query_text = '';
            submittedQueryText = '';
            setTextEmbedding({ queryText: activeImage!, embedding });
        },
        onError: showError
    });

    const { dragOver, handleDragOver, handleDragLeave, handleDrop, handlePaste, handleFileSelect } =
        useImageUploadHandlers({
            uploadFile,
            setActiveImage: (name) => (activeImage = name),
            setPreviewUrl: (url) => {
                if (previewUrl) URL.revokeObjectURL(previewUrl);
                previewUrl = url;
            },
            onError: showError
        });

    const embedTextQuery = $derived(
        useEmbedText({ collectionId, queryText: submittedQueryText, embeddingModelId: null })
    );

    function onKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter') submittedQueryText = query_text.trim();
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

    $effect(() => {
        if (activeImage) return;

        if ($embedTextQuery.isError && $embedTextQuery.error) {
            const queryError = $embedTextQuery.error as
                | { error?: unknown; message?: string }
                | Error;
            const message = 'error' in queryError ? queryError.error : queryError.message;
            showError(String(message));
            return;
        }

        if (!submittedQueryText) {
            setTextEmbedding(undefined);
            return;
        }

        if ($embedTextQuery.isSuccess) {
            setTextEmbedding({ queryText: submittedQueryText, embedding: $embedTextQuery.data });
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
    {#if activeImage || submittedQueryText}
        <ActiveSearchDisplay
            {activeImage}
            {submittedQueryText}
            {previewUrl}
            dragOver={$dragOver}
            onClearImage={clearSearch}
            onClearText={() => {
                submittedQueryText = '';
            }}
        />
    {:else}
        <SearchInput
            bind:queryText={query_text}
            isUploading={$isUploading}
            dragOver={$dragOver}
            onkeydown={onKeyDown}
            onpaste={handlePaste}
            triggerFileInput={() => fileInput?.click()}
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
