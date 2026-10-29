<script lang="ts">
    import { writable } from 'svelte/store';
    import { Button } from '$lib/components/ui/button';
    import * as Alert from '$lib/components/ui/alert/index.js';
    import { LIGHTLYTRAIN_SNIPPET, TRAIN_WITH_LIGHTLYTRAIN_DOCS_URL } from './lightlyTrainSnippet';

    const isCopied = writable(false);

    const copySnippet = async () => {
        await navigator.clipboard.writeText(LIGHTLYTRAIN_SNIPPET);
        isCopied.set(true);
    };
</script>

<Alert.Root class="border text-foreground" data-testid="train-with-lightlytrain">
    <div class="flex flex-col gap-2 text-sm">
        <p>Unzip <code>coco_export.zip</code>, then train a detector on it with LightlyTrain:</p>
        <pre class="max-h-48 overflow-auto rounded bg-muted p-2 text-xs"><code
                >{LIGHTLYTRAIN_SNIPPET}</code
            ></pre>
        <div class="flex items-center justify-between gap-2">
            <a
                class="text-primary underline"
                href={TRAIN_WITH_LIGHTLYTRAIN_DOCS_URL}
                target="_blank"
                rel="noopener noreferrer">Train a detector with LightlyTrain</a
            >
            <Button variant="outline" size="sm" onclick={copySnippet}>
                {$isCopied ? 'Copied' : 'Copy code'}
            </Button>
        </div>
    </div>
</Alert.Root>
