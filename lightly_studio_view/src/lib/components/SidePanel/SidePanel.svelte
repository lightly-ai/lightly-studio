<script lang="ts">
    import { Button } from '$lib/components/ui';
    import * as Alert from '$lib/components/ui/alert/index.js';
    import * as Sheet from '$lib/components/ui/sheet/index.js';
    import { CheckCircle2, Loader2 } from '@lucide/svelte';
    import type { Snippet } from 'svelte';
    import { fade } from 'svelte/transition';

    const {
        title,
        submitLabel = 'Submit',
        cancelLabel = 'Cancel',
        errorMessage = '',
        successMessage = '',
        isOpen = false,
        isLoading = false,
        isDisabled = false,
        onSubmit,
        onOpenChange,
        children,
        exportURL
    }: {
        title: string;
        submitLabel?: string;
        cancelLabel?: string;
        errorMessage?: string;
        successMessage?: string;
        isOpen?: boolean;
        isLoading?: boolean;
        isDisabled?: boolean;
        onSubmit: () => void;
        onOpenChange: (open: boolean) => void;
        children: Snippet;
        exportURL?: string;
    } = $props();
</script>

<Sheet.Root open={isOpen} {onOpenChange}>
    <Sheet.Content side="right" class="w-[400px]">
        <Sheet.Header>
            <Sheet.Title>{title}</Sheet.Title>
        </Sheet.Header>

        <div class="mt-6">
            {@render children()}
        </div>

        {#if errorMessage || successMessage}
            <div class="my-4" transition:fade>
                <Alert.Root
                    variant={errorMessage ? 'destructive' : 'default'}
                    class="border text-foreground"
                    data-testid={errorMessage ? 'alert-destructive' : 'alert-success'}
                >
                    <div class="flex items-center gap-2">
                        {#if errorMessage}
                            <span class="text-destructive-foreground">{errorMessage}</span>
                        {:else}
                            <CheckCircle2 class="h-4 w-4 text-primary" />
                            <span>{successMessage}</span>
                        {/if}
                    </div>
                </Alert.Root>
            </div>
        {/if}

        <Sheet.Footer class="mt-6">
            <div class="flex w-full flex-row gap-3">
                <Sheet.Close class="w-full">
                    <Button
                        class="w-full"
                        variant="ghost"
                        disabled={isLoading}
                        data-testid="cancel-button"
                    >
                        {cancelLabel}
                    </Button>
                </Sheet.Close>

                <!-- If we have an export URL, we can use it as a download link -->
                {#if exportURL}
                    <Button
                        class="relative w-full"
                        disabled={isDisabled || isLoading}
                        href={exportURL}
                        target="_blank"
                        data-testid="submit-button"
                    >
                        {submitLabel}
                    </Button>
                {:else}
                    <Button
                        class="relative w-full"
                        disabled={isDisabled || isLoading}
                        onclick={onSubmit}
                        data-testid="submit-button"
                    >
                        {submitLabel}
                        {#if isLoading}
                            <div
                                class="absolute inset-0 flex items-center justify-center backdrop-blur-sm"
                                data-testid="loading-spinner"
                            >
                                <Loader2 class="animate-spin" />
                            </div>
                        {/if}
                    </Button>
                {/if}
            </div>
        </Sheet.Footer>
    </Sheet.Content>
</Sheet.Root>
