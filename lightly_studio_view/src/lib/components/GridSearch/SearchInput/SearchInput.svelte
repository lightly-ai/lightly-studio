<script lang="ts">
    import { Search, Image as ImageIcon } from '@lucide/svelte';
    import Input from '$lib/components/ui/input/input.svelte';

    interface Props {
        queryText: string;
        isUploading: boolean;
        dragOver: boolean;
        onkeydown: (event: KeyboardEvent) => void;
        onpaste: (event: ClipboardEvent) => Promise<void>;
        triggerFileInput: () => void;
    }

    let {
        queryText = $bindable(),
        isUploading,
        dragOver,
        onkeydown,
        onpaste,
        triggerFileInput
    }: Props = $props();
</script>

<div class="relative">
    <Search class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground" />
    <Input
        placeholder={isUploading ? 'Uploading...' : 'Search samples by description or image'}
        class="pl-8 pr-8 {dragOver ? 'ring-2 ring-primary' : ''}"
        bind:value={queryText}
        {onkeydown}
        {onpaste}
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
</div>
