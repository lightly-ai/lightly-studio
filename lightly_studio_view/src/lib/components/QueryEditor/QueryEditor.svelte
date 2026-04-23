<script lang="ts">
    import { onMount } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import { LIGHTLY_QUERY_DEFAULT_VALUE } from './monaco-lightly-query.js';
    import { useLightlyQueryEditor } from './useLightlyQueryEditor.js';
    import type { QueryExprNotificationParams } from './language/query-expr-notification.js';
    import Typography from '$lib/components/Typography/Typography.svelte';

    interface QueryEditorProps {
        value?: string;
        height?: string;
        readOnly?: boolean;
        onSave?: (value: string, parsed: QueryExprNotificationParams | null) => void;
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

    async function handleSave() {
        const parsed = await editor.getLatestParsed();
        onSave?.(value, parsed);
    }

    onMount(() => {
        if (containerEl) {
            editor.mount(containerEl);
        }
    });
</script>

<div
    class="flex w-full flex-col overflow-hidden rounded-lg border border-[#3c3c3c] bg-[#1e1e1e]"
    style={`height: ${height}`}
>
    <div class="min-h-0 flex-1" bind:this={containerEl}></div>
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
                onclick={handleSave}
            >
                <Typography variant="caption">Save</Typography>
            </Button>
        </div>
    {/if}
</div>
