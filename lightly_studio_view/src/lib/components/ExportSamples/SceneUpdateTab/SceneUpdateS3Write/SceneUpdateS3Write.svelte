<script lang="ts">
    import { Button, FormField } from '$lib/components';
    import { Input } from '$lib/components/ui/input';
    import { exportCollectionSceneUpdateWrite } from '$lib/api/lightly_studio_local';

    type WriteBody = Parameters<typeof exportCollectionSceneUpdateWrite>[0]['body'];

    interface Props {
        /** The ID of the collection the export runs on. */
        collectionId: string;
        /** Whether the shared export fields are valid. */
        canExport: boolean;
        /** Builds the request body from the shared export fields. */
        requestBody: () => Omit<WriteBody, 'output_uri'>;
    }

    let { collectionId, canExport, requestBody }: Props = $props();

    // An `s3://` URI with a bucket, e.g. `s3://bucket` or `s3://bucket/prefix`.
    const S3_URI_PATTERN = /^s3:\/\/[^/]+/;

    let bucketUri = $state('');
    let writtenUris = $state<string[]>([]);
    let isWriting = $state(false);
    let writeError = $state('');

    const canWrite = $derived(canExport && S3_URI_PATTERN.test(bucketUri));

    async function handleWrite() {
        isWriting = true;
        writeError = '';
        writtenUris = [];
        try {
            const response = await exportCollectionSceneUpdateWrite({
                path: { collection_id: collectionId },
                body: { ...requestBody(), output_uri: bucketUri }
            });
            if (response.error) throw new Error(JSON.stringify(response.error));
            if (!response.data) throw new Error('Unexpected empty response data');
            writtenUris = response.data.uris;
        } catch (e) {
            writeError = `Export failed: ${String(e)}`;
        } finally {
            isWriting = false;
        }
    }
</script>

<div class="space-y-4 pt-2">
    <FormField label="S3 Bucket">
        <Input bind:value={bucketUri} placeholder="s3://bucket" />
    </FormField>
    <p class="text-sm text-muted-foreground">
        If a file with the same name is already in the bucket, nothing is written and no file is
        overwritten. If the upload fails part-way, the files it wrote are removed, so you can try
        again.
    </p>
    {#if writeError}
        <p class="text-sm text-destructive">{writeError}</p>
    {/if}
    <Button
        variant="default"
        isPending={isWriting}
        buttonProps={{
            class: 'w-full',
            disabled: !canWrite,
            onclick: handleWrite,
            'data-testid': 'scene-update-write-button'
        }}
    >
        Write to cloud
    </Button>
    {#if writtenUris.length > 0}
        <ul class="space-y-1 text-sm">
            {#each writtenUris as uri (uri)}
                <li class="break-all">{uri}</li>
            {/each}
        </ul>
    {/if}
</div>
