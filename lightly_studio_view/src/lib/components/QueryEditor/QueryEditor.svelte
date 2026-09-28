<script lang="ts">
    import { onMount, untrack } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { Button } from '$lib/components';

    import { useQueryEditor } from './useQueryEditor';
    import type { QueryExprTranslationResult } from './language/query-expr-translation';
    import type { RootScope } from './language/types';

    const DEFAULT_VALUES: Record<RootScope, string> = {
        image: `# Example query
width < 500
AND "reviewed" IN tags
AND object_detection(class_name = "person" AND x > 10)
`,
        video: `# Example query
duration_s > 10
AND "reviewed" IN tags
AND object_detection(class_name = "person")
`
    };

    interface QueryEditorProps {
        value?: string;
        /** Top-level scope of the query: the grid that the query filters. */
        rootScope?: RootScope;
        height?: string;
        readOnly?: boolean;
        onSave?: (value: string, parsed: QueryExprTranslationResult | null) => void;
    }

    let {
        value: valueProp,
        rootScope = 'image',
        height = '320px',
        readOnly = false,
        onSave
    }: QueryEditorProps = $props();

    const initialValue = $derived(valueProp ?? DEFAULT_VALUES[rootScope]);

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
        const translationResult = translateQuery(draftValue, rootScope);
        if (translationResult.status === 'error') {
            toast.error(`Failed to translate query: ${formatTranslationErrors(translationResult)}`);
            return;
        }
        onSave?.(draftValue, translationResult);
        lastAppliedValue = draftValue;
    }

    let draftValue = $state(untrack(() => initialValue));
    let lastAppliedValue = $state<string | null>(untrack(() => valueProp ?? null));

    onMount(() => {
        if (!containerEl) return;
        return mount(containerEl, {
            value: initialValue,
            rootScope,
            readOnly,
            onChange: (next) => {
                draftValue = next;
            }
        });
    });
    const canApply = $derived(draftValue !== lastAppliedValue);
</script>

<!-- Prevent keypresses from triggering global shortcuts (e.g. 'E' toggling edit mode) -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    class="flex w-full flex-col overflow-hidden rounded-lg border border-[#3c3c3c] bg-[#1e1e1e]"
    style={`height: ${height}`}
    onkeydown={(e) => e.stopPropagation()}
    onkeyup={(e) => e.stopPropagation()}
>
    <div class="min-h-0 flex-1" bind:this={containerEl}></div>
    {#if onSave}
        <div
            class="flex items-center justify-end gap-2 border-b border-[#3c3c3c] bg-[#252526] px-4 py-2"
        >
            <Button
                variant="default"
                buttonProps={{
                    type: 'button',
                    disabled: readOnly || !canApply,
                    'data-testid': 'query-editor-apply-button',
                    onclick: handleSave
                }}>Apply</Button
            >
        </div>
    {/if}
</div>
