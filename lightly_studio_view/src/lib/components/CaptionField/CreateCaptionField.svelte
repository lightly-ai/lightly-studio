<script lang="ts">
    import { Check, X } from '@lucide/svelte';

    const {
        onCreate,
        isCreatingCaption: controlledIsCreatingCaption,
        onCreatingCaptionChange,
        canStartDraft = true
    }: {
        onCreate: (text: string) => Promise<boolean> | boolean;
        isCreatingCaption?: boolean;
        onCreatingCaptionChange?: (isOpen: boolean) => void;
        canStartDraft?: boolean;
    } = $props();

    let internalIsCreatingCaption = $state(false);
    let newCaptionText = $state('');
    const isCreatingCaption = $derived(controlledIsCreatingCaption ?? internalIsCreatingCaption);

    const setIsCreatingCaption = (isOpen: boolean) => {
        if (onCreatingCaptionChange) {
            onCreatingCaptionChange(isOpen);
            return;
        }
        internalIsCreatingCaption = isOpen;
    };

    const focusOnMount = (inputElement: HTMLInputElement) => {
        inputElement.focus();
    };

    const openCreateCaption = () => {
        if (!canStartDraft) return;
        setIsCreatingCaption(true);
    };

    const cancelCreateCaption = () => {
        setIsCreatingCaption(false);
        newCaptionText = '';
    };

    const submitCreateCaption = async () => {
        const text = newCaptionText.trim();
        if (!text) return;

        const shouldClose = await onCreate(text);
        if (shouldClose === false) return;

        setIsCreatingCaption(false);
        newCaptionText = '';
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        const isNavigationKey =
            ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key) ||
            event.code === 'Space';

        if (isNavigationKey) {
            event.stopPropagation();
            event.stopImmediatePropagation?.();
        }

        if (event.key !== 'Enter' || event.shiftKey) return;

        event.preventDefault();
        void submitCreateCaption();
    };

    const preventViewerNavigation = (node: HTMLElement) => {
        const listener = (event: Event) => handleKeyDown(event as KeyboardEvent);
        node.addEventListener('keydown', listener, true);
        return {
            destroy: () => node.removeEventListener('keydown', listener, true)
        };
    };
</script>

{#if isCreatingCaption}
    <div class="mb-2 flex items-center gap-2 rounded-sm bg-card px-2 py-2">
        <input
            class="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm"
            type="text"
            bind:value={newCaptionText}
            placeholder="Add caption"
            use:preventViewerNavigation
            use:focusOnMount
            data-testid="new-caption-input"
        />
        <button
            type="button"
            class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-primary bg-primary text-primary-foreground transition disabled:cursor-not-allowed disabled:border-input disabled:bg-background disabled:text-muted-foreground disabled:opacity-50"
            onclick={submitCreateCaption}
            disabled={!newCaptionText.trim()}
            aria-label="Save new caption"
            data-testid="save-new-caption-button"
        >
            <Check class="size-5" />
        </button>
        <button
            type="button"
            class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-input bg-background text-foreground transition hover:bg-muted"
            onclick={cancelCreateCaption}
            aria-label="Cancel new caption"
            data-testid="cancel-new-caption-button"
        >
            <X class="size-5" />
        </button>
    </div>
{:else}
    <button
        type="button"
        class="mb-2 flex h-8 items-center justify-center rounded-sm bg-card px-2 py-0 text-diffuse-foreground transition-colors enabled:hover:bg-primary enabled:hover:text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
        onclick={openCreateCaption}
        disabled={!canStartDraft}
        data-testid="add-caption-button"
    >
        +
    </button>
{/if}
