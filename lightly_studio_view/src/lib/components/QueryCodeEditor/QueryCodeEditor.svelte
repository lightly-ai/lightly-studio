<script lang="ts">
    import loader from '@monaco-editor/loader';
    import * as monaco from 'monaco-editor';
    import { onMount, onDestroy } from 'svelte';
    // Serve Monaco from the Vite bundle (Machine A) instead of cdn.jsdelivr.net.
    // Without this, Machine B's browser would need direct internet access to load the editor.
    loader.config({ monaco });
    import { Play, X } from '@lucide/svelte';
    import type { QueryCompletionsResponse } from '$lib/api/lightly_studio_local/types.gen';

    interface Props {
        onrun: (query: string) => void;
        onclear?: () => void;
        initialValue?: string;
        onchange?: (value: string) => void;
        isQueryActive?: boolean;
    }

    const { onrun, onclear, initialValue, onchange, isQueryActive = false }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let editor: any = $state(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let completionDisposable: any = null;
    let error = $state<string | null>(null);
    let hasPendingChanges = $state(false);

    $effect(() => {
        if (!isQueryActive) hasPendingChanges = false;
    });

    // Display aliases: map backend namespace names to shorter editor-facing names.
    const NAMESPACE_ALIASES: Record<string, string> = {
        ImageSampleField: 'Image'
    };

    const PLACEHOLDER = `Image.width > 1920`;

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

                    // Compute the replacement range: cover the word currently being typed so
                    // accepting a suggestion replaces it rather than appending to it.
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    const wordAtPosition: any = model.getWordAtPosition(position);
                    const range = {
                        startLineNumber: position.lineNumber,
                        endLineNumber: position.lineNumber,
                        startColumn: wordAtPosition?.startColumn ?? position.column,
                        endColumn: wordAtPosition?.endColumn ?? position.column
                    };

                    // Text before the word being typed — used to detect the namespace/field context.
                    const textBeforeWord = wordAtPosition
                        ? lineText.slice(0, wordAtPosition.startColumn - 1)
                        : lineText;

                    // After "Namespace.field." → suggest methods declared by the backend.
                    for (const ns of completions!.namespaces) {
                        const displayName = NAMESPACE_ALIASES[ns.name] ?? ns.name;
                        for (const field of ns.fields) {
                            if (
                                field.methods.length > 0 &&
                                textBeforeWord.endsWith(`${displayName}.${field.name}.`)
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

                    // After "SomeNamespace." → suggest fields.
                    for (const ns of completions!.namespaces) {
                        const displayName = NAMESPACE_ALIASES[ns.name] ?? ns.name;
                        if (textBeforeWord.endsWith(`${displayName}.`)) {
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
                    }

                    // Top-level completions: namespaces + functions (no dot in line).
                    if (!lineText.includes('.')) {
                        for (const ns of completions!.namespaces) {
                            const displayName = NAMESPACE_ALIASES[ns.name] ?? ns.name;
                            items.push({
                                label: displayName,
                                kind: monaco.languages.CompletionItemKind.Class,
                                detail: 'Namespace',
                                documentation: ns.doc,
                                insertText: displayName,
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
            suggest: { showSnippets: true },
            // Render suggestion/hover widgets outside the clipped container so they are
            // always fully visible even when the editor sits inside overflow:hidden.
            fixedOverflowWidgets: true
        });
        editor.onDidChangeModelContent(() => {
            const value = editor.getValue() as string;
            onchange?.(value);
            hasPendingChanges = true;
        });

    });

    onDestroy(() => {
        completionDisposable?.dispose();
        editor?.dispose();
    });

    function runQuery() {
        if (!editor) return;
        // Strip comment lines before sending.
        let raw = (editor.getValue() as string)
            .split('\n')
            .filter((l: string) => !l.trimStart().startsWith('#'))
            .join('\n')
            .trim();
        // Map display aliases back to the backend namespace names.
        for (const [backendName, displayName] of Object.entries(NAMESPACE_ALIASES)) {
            raw = raw.replaceAll(`${displayName}.`, `${backendName}.`);
        }
        if (!raw) return;
        error = null;
        hasPendingChanges = false;
        onrun(raw);
    }
</script>

<div class="flex h-full flex-col gap-2">
    <div class="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
        <p>Filter images using the DatasetQuery API.</p>
        <p class="mt-1">
            Available: <code class="text-xs font-mono">Image</code>, <code class="text-xs font-mono">AND</code>,
            <code class="text-xs font-mono">OR</code>, <code class="text-xs font-mono">NOT</code>
        </p>
        <p class="mt-1">Examples:</p>
        <code class="mt-0.5 block text-xs font-mono">Image.width &gt; 1920</code>
        <code class="mt-1 block text-xs font-mono">AND(Image.width &gt; 1920, Image.tags.contains("cat"))</code>
    </div>

    <div
        bind:this={container}
        class="min-h-[120px] flex-1 overflow-hidden rounded-md border border-input"
    ></div>

    {#if error}
        <p class="text-xs text-destructive">{error}</p>
    {/if}

    <div class="flex justify-end">
        {#if isQueryActive && !hasPendingChanges}
            <button
                class="flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-sm font-medium hover:bg-muted disabled:opacity-50"
                onclick={onclear}
                disabled={!editor}
            >
                <X class="h-3.5 w-3.5" />
                Clear filter
            </button>
        {:else}
            <button
                class="flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                onclick={runQuery}
                disabled={!editor}
            >
                <Play class="h-3.5 w-3.5" />
                Apply
            </button>
        {/if}
    </div>
</div>
