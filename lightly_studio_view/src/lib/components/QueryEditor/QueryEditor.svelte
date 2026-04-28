<script lang="ts">
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { Button } from '$lib/components/ui/button';
    import Typography from '$lib/components/Typography/Typography.svelte';

    import { useQueryEditor, type QueryEditorResponse } from './useQueryEditor';

    const LIGHTLY_QUERY_DEFAULT_VALUE = `Image.width > 1920 AND tags.contains("reviewed")
AND object_detection(label == "car" and x > 10)`;

    export interface QueryEditorProps {
        value?: string;
        height?: string;
        readOnly?: boolean;
        onSave?: (value: string, parsed: QueryEditorResponse | null) => void;
    }

    let {
        value = $bindable(LIGHTLY_QUERY_DEFAULT_VALUE),
        height = '320px',
        readOnly = false,
        onSave
    }: QueryEditorProps = $props();

    let containerEl: HTMLDivElement | null = null;

    const { mount } = useQueryEditor();

    async function handleSave() {}

    onMount(() => {
        if (containerEl) {
            mount(containerEl);
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
