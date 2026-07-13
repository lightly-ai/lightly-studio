<script lang="ts">
    import * as Alert from '$lib/components/ui/alert/index.js';
    import { fade } from 'svelte/transition';

    interface Props {
        /** Error message to display. When empty, the component renders nothing. */
        error: string;
    }

    let { error }: Props = $props();
</script>

{#if error}
    <div transition:fade>
        <Alert.Root
            variant="destructive"
            class="border text-foreground"
            data-testid="alert-destructive"
        >
            <div class="flex items-center gap-2">
                <span class="text-destructive-foreground">{error}</span>
            </div>
        </Alert.Root>
    </div>
{/if}
