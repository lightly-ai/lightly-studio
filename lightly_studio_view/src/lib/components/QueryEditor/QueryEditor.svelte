<script lang="ts">
    import { onMount } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import { LIGHTLY_QUERY_DEFAULT_VALUE } from './monaco-lightly-query.js';
    import { useLightlyQueryEditor } from './useLightlyQueryEditor.js';
    import Typography from '../Typography/Typography.svelte';

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

<div class="w-full overflow-hidden rounded-lg border border-[#3c3c3c] bg-[#1e1e1e]">
    <div style={`height: ${height}`} bind:this={containerEl}></div>
    {#if onSave}
        <div
            class="flex items-center justify-end gap-2 border-b border-[#3c3c3c] bg-[#252526] px-2 py-1 text-xs text-[#cccccc]"
        >
            <Button
                type="button"
                size="sm"
                variant="ghost"
                class="h-6 px-2 text-[#cccccc] hover:bg-white/10 hover:text-white"
                disabled={readOnly}
                onclick={() => onSave?.(value)}
            >
                <Typography variant="caption">Save</Typography>
            </Button>
        </div>
    {/if}
</div>
