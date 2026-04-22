<script lang="ts">
    import { onMount } from 'svelte';
    import { LIGHTLY_QUERY_DEFAULT_VALUE } from './monaco-lightly-query.js';
    import { useLightlyQueryEditor } from './useLightlyQueryEditor.js';

    interface QueryEditorProps {
        value?: string;
        height?: string;
        readOnly?: boolean;
    }

    let {
        value = $bindable(LIGHTLY_QUERY_DEFAULT_VALUE),
        height = '320px',
        readOnly = false
    }: QueryEditorProps = $props();

    let containerEl: HTMLDivElement | null = null;

    const editor = useLightlyQueryEditor({
        value: () => value,
        onValueChange: (next) => {
            value = next;
        },
        readOnly: () => readOnly
    });

    onMount(() => {
        if (containerEl) {
            editor.mount(containerEl);
        }
    });
</script>

<div class="query-editor" style={`height: ${height}`} bind:this={containerEl}></div>

<style>
    .query-editor {
        width: 100%;
        border: 1px solid rgb(60 60 60);
        border-radius: 0.5rem;
        overflow: hidden;
    }
</style>
