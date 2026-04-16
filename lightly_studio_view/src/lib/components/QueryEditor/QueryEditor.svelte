<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { useQuerySchema } from '$lib/hooks/useQuerySchema/useQuerySchema';
    import { buildCompletionSource } from './completionSource';
    import { buildLintSource } from './lintSource';

    interface Props {
        collectionId: string;
        onExecute: (text: string) => void;
        initialValue?: string;
    }

    let { collectionId, onExecute, initialValue = '' }: Props = $props();

    let editorContainer: HTMLDivElement | undefined = $state();
    let editorView: import('@codemirror/view').EditorView | undefined;

    const { schema } = useQuerySchema(collectionId);

    onMount(async () => {
        const [cmView, cmState, cmAutocomplete, cmLint, qlang] = await Promise.all([
            import('@codemirror/view'),
            import('@codemirror/state'),
            import('@codemirror/autocomplete'),
            import('@codemirror/lint'),
            import('./query-language')
        ]);

        const { EditorView, keymap, placeholder } = cmView;
        const { EditorState } = cmState;
        const { autocompletion, completionKeymap } = cmAutocomplete;
        const { lintKeymap, linter } = cmLint;
        const { queryEditorLanguage } = qlang;

        const completionSource = buildCompletionSource(() => $schema.data);
        const lintSource = buildLintSource(collectionId);

        const state = EditorState.create({
            doc: initialValue,
            extensions: [
                queryEditorLanguage(),
                autocompletion({ override: [completionSource] }),
                linter(lintSource),
                keymap.of([
                    ...completionKeymap,
                    ...lintKeymap,
                    {
                        key: 'Enter',
                        run(view) {
                            const text = view.state.doc.toString().trim();
                            onExecute(text);
                            return true;
                        }
                    },
                    {
                        key: 'Escape',
                        run(view) {
                            view.contentDOM.blur();
                            return false;
                        }
                    }
                ]),
                placeholder('Filter: width > 1024 and has_tag("train")'),
                EditorView.theme({
                    '&': {
                        fontSize: '14px',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace'
                    },
                    '&.cm-focused': { outline: 'none' },
                    '.cm-content': { padding: '6px 8px', minHeight: '36px' },
                    '.cm-line': { padding: '0' }
                }),
                EditorView.lineWrapping,
                EditorView.updateListener.of((update) => {
                    if (update.docChanged) {
                        const text = update.state.doc.toString();
                        if (!text.trim()) {
                            onExecute('');
                        }
                    }
                })
            ]
        });

        editorView = new EditorView({
            state,
            parent: editorContainer!
        });
    });

    onDestroy(() => {
        editorView?.destroy();
    });

    $effect(() => {
        if (!editorView) return;

        const currentValue = editorView.state.doc.toString();
        if (currentValue === initialValue) return;

        editorView.dispatch({
            changes: { from: 0, to: editorView.state.doc.length, insert: initialValue }
        });
    });

    export function clear() {
        if (!editorView) return;
        editorView.dispatch({
            changes: { from: 0, to: editorView.state.doc.length, insert: '' }
        });
    }
</script>

<div
    bind:this={editorContainer}
    class="w-full rounded-md border border-input bg-background text-sm focus-within:ring-2 focus-within:ring-ring"
></div>
