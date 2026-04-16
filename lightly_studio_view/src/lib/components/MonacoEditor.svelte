<script lang="ts">
  import { onMount } from 'svelte';
  import loader from '@monaco-editor/loader';
  import type { editor } from 'monaco-editor';

  interface Props {
    value?: string;
    language?: string;
    theme?: 'vs' | 'vs-dark' | 'hc-black';
    height?: string;
    width?: string;
    readOnly?: boolean;
    minimap?: boolean;
    lineNumbers?: 'on' | 'off' | 'relative' | 'interval';
    wordWrap?: 'off' | 'on' | 'wordWrapColumn' | 'bounded';
    fontSize?: number;
    tabSize?: number;
    automaticLayout?: boolean;
    onChange?: (value: string) => void;
    onEditorMount?: (editor: editor.IStandaloneCodeEditor) => void;
  }

  let {
    value = $bindable(''),
    language = 'javascript',
    theme = 'vs-dark',
    height = '600px',
    width = '100%',
    readOnly = false,
    minimap = true,
    lineNumbers = 'on',
    wordWrap = 'off',
    fontSize = 14,
    tabSize = 2,
    automaticLayout = true,
    onChange,
    onEditorMount
  }: Props = $props();

  let container = $state<HTMLDivElement>();
  let editorInstance = $state<editor.IStandaloneCodeEditor | null>(null);
  let monaco = $state<typeof import('monaco-editor') | null>(null);

  onMount(() => {
    initializeEditor();

    return () => {
      if (editorInstance) {
        editorInstance.dispose();
      }
    };
  });

  async function initializeEditor() {
    try {
      // Load Monaco Editor
      monaco = await loader.init();

      if (!container) return;

      // Create editor instance
      editorInstance = monaco.editor.create(container, {
        value,
        language,
        theme,
        readOnly,
        minimap: {
          enabled: minimap
        },
        lineNumbers,
        wordWrap,
        fontSize,
        tabSize,
        automaticLayout,
        scrollBeyondLastLine: false,
        renderWhitespace: 'selection',
        contextmenu: true,
        folding: true,
        renderLineHighlight: 'all',
        scrollbar: {
          verticalScrollbarSize: 10,
          horizontalScrollbarSize: 10
        }
      });

      // Set up change listener
      editorInstance.onDidChangeModelContent(() => {
        const currentValue = editorInstance?.getValue() ?? '';
        value = currentValue;
        if (onChange) {
          onChange(currentValue);
        }
      });

      // Call onEditorMount callback if provided
      if (onEditorMount && editorInstance) {
        onEditorMount(editorInstance);
      }
    } catch (error) {
      console.error('Failed to load Monaco Editor:', error);
    }
  }

  // Update editor value when prop changes
  $effect(() => {
    if (editorInstance && value !== editorInstance.getValue()) {
      editorInstance.setValue(value);
    }
  });

  // Update editor options when props change
  $effect(() => {
    if (editorInstance) {
      editorInstance.updateOptions({
        theme,
        readOnly,
        lineNumbers,
        wordWrap,
        fontSize,
        tabSize
      });
    }
  });

  // Update language when prop changes
  $effect(() => {
    if (editorInstance && monaco) {
      const model = editorInstance.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, language);
      }
    }
  });
</script>

<div
  bind:this={container}
  class="monaco-editor-container"
  style:height={height}
  style:width={width}
/>

<style>
  .monaco-editor-container {
    border: 1px solid var(--border-color, #2d2d2d);
    border-radius: 4px;
    overflow: hidden;
  }
</style>