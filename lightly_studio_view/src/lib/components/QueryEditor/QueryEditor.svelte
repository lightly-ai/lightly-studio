<script lang="ts">
    import { onMount } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import { LIGHTLY_QUERY_DEFAULT_VALUE } from './monaco-lightly-query.js';
    import { useLightlyQueryEditor } from './useLightlyQueryEditor.js';

    interface QueryEditorProps {
        value?: string;
        height?: string;
        readOnly?: boolean;
        onSave?: (value: string) => void;
    }

    let {
        value = $bindable(LIGHTLY_QUERY_DEFAULT_VALUE),
        height = '320px',
        readOnly = false,
        onSave
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

<div class="query-editor">
    <div class="query-editor__surface" style={`height: ${height}`} bind:this={containerEl}></div>
    {#if onSave}
        <div class="query-editor__toolbar">
            <Button
                type="button"
                size="sm"
                variant="ghost"
                class="query-editor__action"
                disabled={readOnly}
                onclick={() => onSave?.(value)}
            >
                Save
            </Button>
        </div>
    {/if}
</div>

<style>
    .query-editor {
        width: 100%;
        border: 1px solid rgb(60 60 60);
        border-radius: 0.5rem;
        overflow: hidden;
        background: #1e1e1e;
    }

    .query-editor__toolbar {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.5rem;
        padding: 0.25rem 0.5rem;
        background: #252526;
        border-bottom: 1px solid rgb(60 60 60);
        font-family:
            ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
            monospace;
        font-size: 12px;
        color: #cccccc;
    }

    .query-editor :global(.query-editor__action) {
        height: 1.5rem;
        padding: 0 0.5rem;
        color: #cccccc;
    }

    .query-editor :global(.query-editor__action:hover) {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }
</style>
