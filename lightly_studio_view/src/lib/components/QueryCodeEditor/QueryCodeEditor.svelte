<script lang="ts">
    import loader from '@monaco-editor/loader';
    import * as monaco from 'monaco-editor';
    import { onMount, onDestroy } from 'svelte';
    // Serve Monaco from the Vite bundle (Machine A) instead of cdn.jsdelivr.net.
    // Without this, Machine B's browser would need direct internet access to load the editor.
    loader.config({ monaco });
    import { Play } from '@lucide/svelte';

    interface MethodMeta {
        name: string;
        detail: string;
        insert_text: string;
        doc: string;
    }
    interface FieldMeta {
        name: string;
        kind: string;
        operators: string[];
        methods: MethodMeta[];
        doc: string;
    }
    interface NamespaceMeta {
        name: string;
        doc: string;
        fields: FieldMeta[];
    }
    interface FunctionMeta {
        name: string;
        signature: string;
        doc: string;
    }
    interface QueryCompletionsResponse {
        namespaces: NamespaceMeta[];
        functions: FunctionMeta[];
    }

    interface Props {
        onrun: (query: string) => void;
        initialValue?: string;
        onchange?: (value: string) => void;
    }

    const { onrun, initialValue, onchange }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let editor: any = $state(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let completionDisposable: any = null;
    let error = $state<string | null>(null);

    const PLACEHOLDER = `# Filter images using the DatasetQuery API.
# Available: ImageSampleField, AND, OR, NOT
# Examples:
#   ImageSampleField.width > 1920
#   AND(ImageSampleField.width > 1920, ImageSampleField.tags.contains("cat"))

ImageSampleField.width > 1920`;

    onMount(async () => {
        const monaco = await loader.init();


        // Fetch completion metadata from the backend.
        let completions: QueryCompletionsResponse | null = null;
        try {
            const res = await fetch('/api/query_completions');
            if (res.ok) completions = (await res.json()) as QueryCompletionsResponse;
        } catch {
            // completions will remain null; editor still works without them
        }

        // Register completion provider for Python.
        if (completions) {
            completionDisposable = monaco.languages.registerCompletionItemProvider('python', {
                triggerCharacters: ['.'],
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                provideCompletionItems(model: any, position: any) {
                    const lineText = model.getValueInRange({
                        startLineNumber: position.lineNumber,
                        startColumn: 1,
                        endLineNumber: position.lineNumber,
                        endColumn: position.column
                    }) as string;

                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    const items: any[] = [];
                    const range = {
                        startLineNumber: position.lineNumber,
                        endLineNumber: position.lineNumber,
                        startColumn: position.column,
                        endColumn: position.column
                    };

                    // After "SomeNamespace." → suggest fields.
                    for (const ns of completions!.namespaces) {
                        if (lineText.endsWith(`${ns.name}.`)) {
                            for (const field of ns.fields) {
                                items.push({
                                    label: field.name,
                                    kind: monaco.languages.CompletionItemKind.Field,
                                    detail: field.kind,
                                    documentation: field.doc,
                                    insertText:
                                        field.methods.length > 0
                                            ? `${field.name}.${field.methods[0].insert_text}`
                                            : `${field.name} `,
                                    insertTextRules:
                                        monaco.languages.CompletionItemInsertTextRule
                                            .InsertAsSnippet,
                                    range
                                });
                            }
                            return { suggestions: items };
                        }

                        // After "Namespace.field." → suggest methods declared by the backend.
                        for (const field of ns.fields) {
                            if (
                                field.methods.length > 0 &&
                                lineText.endsWith(`${ns.name}.${field.name}.`)
                            ) {
                                for (const method of field.methods) {
                                    items.push({
                                        label: method.name,
                                        kind: monaco.languages.CompletionItemKind.Method,
                                        detail: method.detail,
                                        documentation: method.doc,
                                        insertText: method.insert_text,
                                        insertTextRules:
                                            monaco.languages.CompletionItemInsertTextRule
                                                .InsertAsSnippet,
                                        range
                                    });
                                }
                                return { suggestions: items };
                            }
                        }
                    }

                    // Top-level completions: namespaces + functions.
                    if (!lineText.includes('.')) {
                        for (const ns of completions!.namespaces) {
                            items.push({
                                label: ns.name,
                                kind: monaco.languages.CompletionItemKind.Class,
                                detail: 'Namespace',
                                documentation: ns.doc,
                                insertText: ns.name,
                                range
                            });
                        }
                        for (const fn of completions!.functions) {
                            items.push({
                                label: fn.name,
                                kind: monaco.languages.CompletionItemKind.Function,
                                detail: fn.signature,
                                documentation: fn.doc,
                                insertText: `${fn.name}($1)`,
                                insertTextRules:
                                    monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                range
                            });
                        }
                    }

                    return { suggestions: items };
                }
            });
        }

        editor = monaco.editor.create(container!, {
            value: initialValue ?? PLACEHOLDER,
            language: 'python',
            theme: 'vs-dark',
            minimap: { enabled: false },
            lineNumbers: 'off',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            fontSize: 13,
            padding: { top: 8, bottom: 8 },
            automaticLayout: true,
            suggest: { showSnippets: true }
        });
        if (onchange) {
            editor.onDidChangeModelContent(() => {
                onchange(editor.getValue() as string);
            });
        }
    });

    onDestroy(() => {
        completionDisposable?.dispose();
        editor?.dispose();
    });

    function runQuery() {
        if (!editor) return;
        // Strip comment lines before sending.
        const raw = (editor.getValue() as string)
            .split('\n')
            .filter((l: string) => !l.trimStart().startsWith('#'))
            .join('\n')
            .trim();
        if (!raw) return;
        error = null;
        onrun(raw);
    }
</script>

<div class="flex h-full flex-col gap-2">
    <div
        bind:this={container}
        class="min-h-[120px] flex-1 overflow-hidden rounded-md border border-input"
    ></div>

    {#if error}
        <p class="text-xs text-destructive">{error}</p>
    {/if}

    <div class="flex justify-end">
        <button
            class="flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            onclick={runQuery}
            disabled={!editor}
        >
            <Play class="h-3.5 w-3.5" />
            Run
        </button>
    </div>
</div>
