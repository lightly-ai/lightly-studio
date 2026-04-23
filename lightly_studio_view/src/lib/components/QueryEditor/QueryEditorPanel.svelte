<script lang="ts">
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';

    const handleQueryEditorValueChange = (value: string) => {
        console.log('Saved query editor value:', value);
    };
    let queryEditorValue = $state('');

    $inspect(queryEditorValue);
</script>

<div class="flex h-full flex-1 flex-col rounded-[1vw] bg-card p-4">
    <QueryEditor
        height="100%"
        bind:value={queryEditorValue}
        onSave={handleQueryEditorValueChange}
    />
</div>
