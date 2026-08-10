<script lang="ts">
    import { Button } from '$lib/components';
    import * as Alert from '$lib/components/ui/alert/index.js';
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
    variant="default"
    isPending={isLoading}
    buttonProps={{
        class: 'my-4 w-full',
        disabled,
        onclick,
        'data-testid': testId
    }}
>
    Download
</Button>
