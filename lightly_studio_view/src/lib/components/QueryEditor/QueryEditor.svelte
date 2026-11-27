<script lang="ts">
    import { onMount, untrack, type Snippet } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { Button } from '$lib/components';

    import { useQueryEditor } from './useQueryEditor';
    import { getDefaultQuery } from './getDefaultQuery';
    import type { QueryExprTranslationResult } from './language/query-expr-translation';

    interface QueryEditorProps {
        value?: string;
        /** Text to show when the editor mounts, in place of `value`. It does not count as applied. */
        draft?: string;
        sampleType?: 'image' | 'video';
        height?: string;
        readOnly?: boolean;
        /** Names of the existing tags. Unknown tags get a warning. Undefined skips the check. */
        tagNames?: string[];
        onSave?: (value: string, parsed: QueryExprTranslationResult) => void;
        /** Extra controls in the footer, before the apply button. Needs `onSave`. */
        footerActions?: Snippet;
    }

    let {
        value: valueProp,
        draft,
        sampleType,
        height = '320px',
        readOnly = false,
        tagNames,
        onSave,
        footerActions
    }: QueryEditorProps = $props();

    const initialValue = $derived(draft ?? valueProp ?? getDefaultQuery(sampleType));

    let containerEl: HTMLDivElement | null = null;

    const { mount, translateQuery, setTagNames } = useQueryEditor();

    $effect(() => setTagNames(tagNames));

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
        const translationResult = translateQuery(draftValue, sampleType);
        if (translationResult.status === 'error') {
            toast.error(`Failed to translate query: ${formatTranslationErrors(translationResult)}`);
            return;
        }
        onSave?.(draftValue, translationResult);
    }

    let draftValue = $state(untrack(() => initialValue));

    onMount(() => {
        if (!containerEl) return;
        return mount(containerEl, {
            value: initialValue,
            readOnly,
            sampleType,
            onChange: (next) => {
                draftValue = next;
            }
        });
    });
    const applyLabel = $derived(draftValue === valueProp ? 'Re-apply' : 'Apply');
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
            {@render footerActions?.()}
            <Button
                variant="default"
                buttonProps={{
                    type: 'button',
                    disabled: readOnly,
                    'data-testid': 'query-editor-apply-button',
                    onclick: handleSave
                }}
            >
                {applyLabel}
            </Button>
        </div>
    {/if}
</div>
