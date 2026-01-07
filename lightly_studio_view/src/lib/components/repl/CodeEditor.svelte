<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import * as monaco from 'monaco-editor';

    export let value = '';
    export let language = 'python';
    
    let editorContainer: HTMLElement;
    let editor: monaco.editor.IStandaloneCodeEditor;

    onMount(() => {
        editor = monaco.editor.create(editorContainer, {
            value: value,
            language: language,
            theme: 'vs-dark',
            minimap: { enabled: false },
            automaticLayout: true,
            scrollBeyondLastLine: false,
            fontSize: 14,
        });

        editor.onDidChangeModelContent(() => {
            value = editor.getValue();
        });
        
        // Add Shift+Enter command to run code
        editor.addCommand(monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => {
            dispatch('run');
        });
    });

    onDestroy(() => {
        if (editor) {
            editor.dispose();
        }
    });

    import { createEventDispatcher } from 'svelte';
    const dispatch = createEventDispatcher();
</script>

<div class="h-full w-full overflow-hidden rounded-md border border-gray-700" bind:this={editorContainer}></div>
