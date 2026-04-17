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

    let editorContainer: HTMLDivElement | null = null;
    let editorView: import('@codemirror/view').EditorView | undefined;
    let initError: string | null = $state(null);

    const { schema } = useQuerySchema(collectionId);

    onMount(() => {
        let destroyed = false;

        async function initializeEditor() {
            if (!editorContainer) {
                return;
            }

            try {
                const [cmView, cmState, cmAutocomplete, cmLint, qlang] = await Promise.all([
                    import('@codemirror/view'),
                    import('@codemirror/state'),
                    import('@codemirror/autocomplete'),
                    import('@codemirror/lint'),
                    import('./query-language-support')
                ]);

                if (destroyed || !editorContainer) {
                    return;
                }

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
                        placeholder('width > 1024 and has_tag("train")'),
                        EditorView.contentAttributes.of({
                            'aria-label': 'Query editor',
                            autocapitalize: 'off',
                            autocomplete: 'off',
                            autocorrect: 'off',
                            spellcheck: 'false'
                        }),
                        EditorView.theme({
                            '&': {
                                minHeight: '40px',
                                color: 'hsl(var(--foreground))',
                                fontSize: '14px',
                                lineHeight: '24px',
                                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace'
                            },
                            '&.cm-focused': { outline: 'none' },
                            '.cm-scroller': { minHeight: '40px' },
                            '.cm-gutters': {
                                backgroundColor: 'transparent',
                                color: 'hsl(var(--muted-foreground))',
                                border: 'none'
                            },
                            '.cm-content': {
                                caretColor: 'hsl(var(--foreground))',
                                padding: '10px 8px 6px',
                                minHeight: '40px',
                                boxSizing: 'border-box'
                            },
                            '.cm-cursor, .cm-dropCursor': {
                                borderLeftColor: 'hsl(var(--foreground))',
                                borderLeftWidth: '2px'
                            },
                            '&.cm-focused .cm-selectionBackground, ::selection': {
                                backgroundColor: 'hsl(var(--accent) / 0.85)'
                            },
                            '.cm-activeLine': {
                                backgroundColor: 'transparent'
                            },
                            '.cm-placeholder': {
                                color: 'hsl(var(--muted-foreground))'
                            },
                            '.cm-tooltip': {
                                zIndex: '30',
                                border: '1px solid hsl(var(--border-hard))',
                                backgroundColor: 'hsl(var(--popover))',
                                color: 'hsl(var(--popover-foreground))',
                                borderRadius: 'calc(var(--radius) - 2px)',
                                boxShadow:
                                    '0 12px 32px hsl(var(--background) / 0.45), 0 0 0 1px hsl(var(--border) / 0.35)'
                            },
                            '.cm-tooltip.cm-tooltip-autocomplete > ul': {
                                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                                maxHeight: '220px'
                            },
                            '.cm-tooltip.cm-tooltip-autocomplete > ul > li': {
                                padding: '6px 10px',
                                color: 'hsl(var(--popover-foreground))'
                            },
                            '.cm-tooltip.cm-tooltip-autocomplete > ul > li[aria-selected]': {
                                backgroundColor: 'hsl(var(--accent))',
                                color: 'hsl(var(--accent-foreground))'
                            },
                            '.cm-tooltip-autocomplete ul li .cm-completionLabel': {
                                color: 'inherit'
                            },
                            '.cm-tooltip-autocomplete ul li .cm-completionDetail': {
                                color: 'hsl(var(--muted-foreground))'
                            },
                            '.cm-tooltip.cm-tooltip-autocomplete ul li[aria-selected] .cm-completionDetail':
                                {
                                    color: 'hsl(var(--accent-foreground) / 0.8)'
                                },
                            '.cm-tooltip-lint': {
                                padding: '8px 10px'
                            },
                            '.cm-diagnostic': {
                                fontFamily: 'inherit'
                            },
                            '.cm-line': {
                                padding: '0',
                                lineHeight: '19.6px'
                            }
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
                    parent: editorContainer
                });
                initError = null;
            } catch (error) {
                initError =
                    error instanceof Error ? error.message : 'Failed to initialize query editor';
            }
        }

        void initializeEditor();

        return () => {
            destroyed = true;
        };
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
    aria-label="Query editor"
    class="mt-3 min-h-10 w-full overflow-hidden rounded-md border border-input bg-background text-sm focus-within:ring-2 focus-within:ring-ring"
></div>
{#if initError}
    <p class="mt-2 text-sm text-destructive">{initError}</p>
{/if}
