// Generic Monaco editor composable. Owns the editor + model lifecycle and
// keeps the editor's value and readOnly option in sync with reactive sources
// supplied by the caller. Language-specific concerns (LSP, registration) live
// one layer up in `useLightlyQueryEditor`.

import * as monaco from 'monaco-editor';
import { onDestroy } from 'svelte';

export interface UseMonacoEditorOptions {
    // Monaco language ID the model is assigned to. Must already be registered
    // via `monaco.languages.register` before `mount()` runs.
    language: string;

    // Monaco theme ID applied to the editor. Must already be defined via
    // `monaco.editor.defineTheme`.
    theme: string;

    // Reactive getter for the editor's current value. Read inside `$effect`,
    // so any reactive state it closes over will push updates into the editor
    // (guarded by a diff-check to avoid clobbering the user's cursor).
    value: () => string;

    // Write-back callback invoked on every edit. This is the other half of
    // two-way value binding — the caller typically assigns to its own
    // `$bindable` prop here.
    onValueChange: (value: string) => void;

    // Reactive getter for the readOnly flag. Optional; defaults to false.
    // Tracked in a `$effect` so toggling it at runtime updates the editor.
    readOnly?: () => boolean;
}

export interface MonacoEditorHandle {
    // Creates the editor inside `container`. Call once from `onMount`.
    mount: (container: HTMLElement) => void;
}

export function useMonacoEditor(options: UseMonacoEditorOptions): MonacoEditorHandle {
    let editor: monaco.editor.IStandaloneCodeEditor | null = null;
    let model: monaco.editor.ITextModel | null = null;

    // Push external value changes into the editor, but only when they differ
    // from the current buffer — setValue resets cursor and undo stack, so
    // echoing the user's own keystrokes back would be disruptive.
    $effect(() => {
        const nextValue = options.value();
        if (editor && editor.getValue() !== nextValue) {
            editor.setValue(nextValue);
        }
    });

    $effect(() => {
        const readOnly = options.readOnly?.() ?? false;
        if (editor && editor.getOption(monaco.editor.EditorOption.readOnly) !== readOnly) {
            editor.updateOptions({ readOnly });
        }
    });

    function mount(container: HTMLElement): void {
        // Every Monaco model needs a unique URI — it's the key the editor.
        const uri = monaco.Uri.parse(`inmemory://model/lightly-query.lql`);
        model = monaco.editor.createModel(options.value(), options.language, uri);

        editor = monaco.editor.create(container, {
            model,
            theme: options.theme,
            readOnly: options.readOnly?.() ?? false,
            automaticLayout: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13
        });

        editor.onDidChangeModelContent(() => {
            if (editor) {
                options.onValueChange(editor.getValue());
            }
        });
    }

    onDestroy(() => {
        editor?.dispose();
        model?.dispose();
        editor = null;
        model = null;
    });

    return { mount };
}
