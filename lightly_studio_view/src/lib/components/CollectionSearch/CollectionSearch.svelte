<!--
  Presentational orchestrator for collection search input.
  Owns transient UI state (typing buffer, drag/drop, file input) and emits user
  intent. The parent owns embedding/upload requests and passes back the resulting
  image chip + pending state.
-->
<script lang="ts">
    import { useFileDrop } from '$lib/hooks';
    import { CollectionSearchInput, CollectionSearchImage } from '$lib/components';

    type ImageState = {
        name: string;
        previewUrl: string;
    };

    type Props = {
        image: ImageState | undefined;
        isPending?: boolean;
        initialQueryText?: string;
        onSubmitText: (text: string) => void;
        onSubmitFile: (file: File) => void | Promise<void>;
        onClear: () => void;
        onError: (message: string) => void;
    };

    let {
        image,
        isPending = false,
        initialQueryText = '',
        onSubmitText,
        onSubmitFile,
        onClear,
        onError
    }: Props = $props();

    let queryText = $state(initialQueryText);
    let submittedQueryText = $state(initialQueryText);
    let fileInput = $state<HTMLInputElement | null>(null);

    const { dragOver, handleDragOver, handleDragLeave, handleDrop, handlePaste, handleFileSelect } =
        useFileDrop({
            onFileAccepted: async (file) => {
                await onSubmitFile(file);
            },
            onError
        });

    const handleClear = () => {
        queryText = '';
        submittedQueryText = '';
        onClear();
    };

    const triggerFileInput = () => {
        fileInput?.click();
    };

    function onKeyDown(event: KeyboardEvent) {
        const input = event.currentTarget as HTMLInputElement | null;

        if (event.key === 'Enter') {
            event.preventDefault();
            const trimmed = queryText.trim();
            if (!trimmed) {
                handleClear();
                input?.blur();
                return;
            }
            queryText = trimmed;
            submittedQueryText = trimmed;
            onSubmitText(trimmed);
            input?.blur();
            return;
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            queryText = submittedQueryText;
            input?.blur();
        }
    }
</script>

<div
    class="relative"
    role="region"
    aria-label="Search by image or text"
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    ondrop={handleDrop}
>
    {#if image}
        <CollectionSearchImage
            name={image.name}
            src={image.previewUrl}
            showOutline={$dragOver}
            onClear={handleClear}
        />
    {:else}
        <CollectionSearchInput
            bind:value={queryText}
            disabled={isPending}
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
        disabled={isPending}
    />
</div>
