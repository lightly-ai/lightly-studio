<script lang="ts">
    import { Button } from '$lib/components/ui';
    import { Loader2 } from '@lucide/svelte';

    interface Props {
        /** Called when the button is clicked. */
        onclick: () => void;
        /** When true, the button is non-interactive. */
        disabled?: boolean;
        /** When true, a spinner overlay is shown on the button. */
        isLoading?: boolean;
        /** Value for the data-testid attribute. */
        testId: string;
    }

    let { onclick, disabled = false, isLoading = false, testId }: Props = $props();
</script>

<Button class="relative my-4 w-full" {disabled} {onclick} data-testid={testId}>
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
