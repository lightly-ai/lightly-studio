<script lang="ts">
    import { Button } from '$lib/components/ui';
    import * as Alert from '$lib/components/ui/alert/index.js';
    import { Loader2 } from '@lucide/svelte';
    import { fade } from 'svelte/transition';

    interface Props {
        /** Whether the download is in progress. Disables the button and shows a spinner. */
        isLoading: boolean;
        /** Whether the button is disabled independently of loading state. */
        disabled?: boolean;
        /** Called when the user clicks the button. */
        onclick: () => void;
        /** Test ID for the button element. */
        testId?: string;
        /** Error message to display above the button. Hidden when empty. */
        errorMessage?: string;
    }

    let {
        isLoading,
        disabled = false,
        onclick,
        testId = 'export-download-button',
        errorMessage = ''
    }: Props = $props();
</script>

{#if errorMessage}
    <div transition:fade>
        <Alert.Root variant="destructive" class="border text-foreground">
            <span class="text-destructive-foreground">{errorMessage}</span>
        </Alert.Root>
    </div>
{/if}

<Button
    class="relative my-4 w-full"
    disabled={disabled || isLoading}
    {onclick}
    data-testid={testId}
>
    Download
    {#if isLoading}
        <div
            class="absolute inset-0 flex items-center justify-center backdrop-blur-sm"
            data-testid="loading-spinner"
        >
            <Loader2 class="animate-spin" />
        </div>
    {/if}
</Button>
