<script lang="ts">
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { Button } from '$lib/components/ui/button';

    import { useQueryEditor } from './useQueryEditor';
    import type { QueryExprTranslationResult } from './language/query-expr-translation';

    const LIGHTLY_QUERY_DEFAULT_VALUE = `width > 1920 AND ("reviewed" IN tags)
AND object_detection(label == "car" and x > 10)`;

    interface QueryEditorProps {
        value?: string;
        height?: string;
        readOnly?: boolean;
        onSave?: (value: string, parsed: QueryExprTranslationResult | null) => void;
    }

    let {
        value = $bindable(LIGHTLY_QUERY_DEFAULT_VALUE),
        height = '320px',
        readOnly = false,
        onSave
    }: QueryEditorProps = $props();

    let containerEl: HTMLDivElement | null = null;

    const { mount, translateQuery } = useQueryEditor();

    function formatTranslationErrors(
        result: Extract<QueryExprTranslationResult, { status: 'error' }>
    ): string {
        return result.errors
            .map((error) => {
                if (error.line !== undefined && error.column !== undefined) {
                    return `${error.message} (line ${error.line}, column ${error.column})`;
                }
                return error.message;
            })
            .join('\n');
    }

    function handleSave() {
        const translationResult = translateQuery(draftValue);
        if (translationResult.status === 'error') {
            toast.error(`Failed to translate query: ${formatTranslationErrors(translationResult)}`);
            return;
        }
        onSave?.(draftValue, translationResult);
    }

    let draftValue = $state(value);

    onMount(() => {
        if (!containerEl) return;
        return mount(containerEl, {
            value,
            readOnly,
            onChange: (next) => {
                draftValue = next;
            }
        });
    });
    const isModified = $derived(value !== draftValue);
</script>

<div
    class="flex w-full flex-col overflow-hidden rounded-lg border border-[#3c3c3c] bg-[#1e1e1e]"
    style={`height: ${height}`}
>
    <div class="min-h-0 flex-1" bind:this={containerEl}></div>
    {#if onSave}
        <div
            class="flex items-center justify-end gap-2 border-b border-[#3c3c3c] bg-[#252526] px-4 py-2"
        >
            <Button type="button" disabled={readOnly || !isModified} onclick={handleSave}
                >Apply</Button
            >
        </div>
    {/if}
</div>
