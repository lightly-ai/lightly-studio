<script lang="ts">
    import CollectionSearchBar from './CollectionSearchBar.svelte';

    type TestCase =
        | 'default'
        | 'active-image'
        | 'active-image-with-preview'
        | 'uploading'
        | 'drag-over'
        | 'submitted-query';

    let { testCase = 'default' }: { testCase?: TestCase } = $props();

    const noop = () => {};
    const noopStr = (_: string) => {};
    const noopEvent = (_: Event) => {};
    const noopKeyboard = (_: KeyboardEvent) => {};
    const noopClipboard = (_: ClipboardEvent) => {};
    const noopDrag = (_: DragEvent) => {};
</script>

{#if testCase === 'default'}
    <CollectionSearchBar
        queryText=""
        submittedQueryText=""
        activeImage={null}
        previewUrl={null}
        onQueryTextInput={noopStr}
        onKeyDown={noopKeyboard}
        onPaste={noopClipboard}
        onDragOver={noopDrag}
        onDragLeave={noopDrag}
        onDrop={noopDrag}
        onClearSearch={noop}
        onFileSelect={noopEvent}
    />
{:else if testCase === 'active-image'}
    <CollectionSearchBar
        queryText=""
        submittedQueryText=""
        activeImage="photo.jpg"
        previewUrl={null}
        onQueryTextInput={noopStr}
        onKeyDown={noopKeyboard}
        onPaste={noopClipboard}
        onDragOver={noopDrag}
        onDragLeave={noopDrag}
        onDrop={noopDrag}
        onClearSearch={noop}
        onFileSelect={noopEvent}
    />
{:else if testCase === 'active-image-with-preview'}
    <CollectionSearchBar
        queryText=""
        submittedQueryText=""
        activeImage="photo.jpg"
        previewUrl="blob:preview-url"
        onQueryTextInput={noopStr}
        onKeyDown={noopKeyboard}
        onPaste={noopClipboard}
        onDragOver={noopDrag}
        onDragLeave={noopDrag}
        onDrop={noopDrag}
        onClearSearch={noop}
        onFileSelect={noopEvent}
    />
{:else if testCase === 'uploading'}
    <CollectionSearchBar
        queryText=""
        submittedQueryText=""
        activeImage={null}
        previewUrl={null}
        isUploading={true}
        onQueryTextInput={noopStr}
        onKeyDown={noopKeyboard}
        onPaste={noopClipboard}
        onDragOver={noopDrag}
        onDragLeave={noopDrag}
        onDrop={noopDrag}
        onClearSearch={noop}
        onFileSelect={noopEvent}
    />
{:else if testCase === 'drag-over'}
    <CollectionSearchBar
        queryText=""
        submittedQueryText=""
        activeImage={null}
        previewUrl={null}
        isDragOver={true}
        onQueryTextInput={noopStr}
        onKeyDown={noopKeyboard}
        onPaste={noopClipboard}
        onDragOver={noopDrag}
        onDragLeave={noopDrag}
        onDrop={noopDrag}
        onClearSearch={noop}
        onFileSelect={noopEvent}
    />
{:else if testCase === 'submitted-query'}
    <CollectionSearchBar
        queryText="cats"
        submittedQueryText="cats"
        activeImage={null}
        previewUrl={null}
        onQueryTextInput={noopStr}
        onKeyDown={noopKeyboard}
        onPaste={noopClipboard}
        onDragOver={noopDrag}
        onDragLeave={noopDrag}
        onDrop={noopDrag}
        onClearSearch={noop}
        onFileSelect={noopEvent}
    />
{/if}
