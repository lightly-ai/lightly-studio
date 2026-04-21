<script lang="ts">
    import { onMount } from 'svelte';
    import * as monaco from 'monaco-editor';
    import { MonacoLanguageClient } from 'monaco-languageclient';
    import { CloseAction, ErrorAction } from 'vscode-languageclient';
    import {
        BrowserMessageReader,
        BrowserMessageWriter
    } from 'vscode-languageserver-protocol/browser.js';
    import {
        createLightlyQueryLanguageServerWorker,
        LIGHTLY_QUERY_DEFAULT_VALUE,
        LIGHTLY_QUERY_LANGUAGE_ID,
        LIGHTLY_QUERY_THEME_ID,
        registerLightlyQueryMonacoLanguage
    } from './monaco-lightly-query.js';

    interface QueryEditorProps {
        value?: string;
        height?: string;
        readOnly?: boolean;
    }

    let {
        value = $bindable(LIGHTLY_QUERY_DEFAULT_VALUE),
        height = '320px',
        readOnly = false
    }: QueryEditorProps = $props();

    let containerEl: HTMLDivElement | null = null;

    let editor: monaco.editor.IStandaloneCodeEditor | null = null;
    let languageClient: MonacoLanguageClient | null = null;
    let worker: Worker | null = null;

    function createLanguageClient(languageWorker: Worker): MonacoLanguageClient {
        const reader = new BrowserMessageReader(languageWorker);
        const writer = new BrowserMessageWriter(languageWorker);

        return new MonacoLanguageClient({
            name: 'LightlyQuery Language Client',
            clientOptions: {
                documentSelector: [{ language: LIGHTLY_QUERY_LANGUAGE_ID }],
                errorHandler: {
                    error: () => ({ action: ErrorAction.Continue }),
                    closed: () => ({ action: CloseAction.DoNotRestart })
                }
            },
            messageTransports: { reader, writer }
        });
    }

    onMount(() => {
        if (!containerEl) {
            return;
        }

        registerLightlyQueryMonacoLanguage();

        const modelUri = monaco.Uri.parse(`inmemory://model/${crypto.randomUUID()}.lql`);
        const model = monaco.editor.createModel(value, LIGHTLY_QUERY_LANGUAGE_ID, modelUri);

        editor = monaco.editor.create(containerEl, {
            model,
            theme: LIGHTLY_QUERY_THEME_ID,
            readOnly,
            automaticLayout: true,
            minimap: {
                enabled: false
            },
            scrollBeyondLastLine: false,
            fontSize: 13
        });

        editor.onDidChangeModelContent(() => {
            value = editor?.getValue() ?? value;
        });

        worker = createLightlyQueryLanguageServerWorker();
        languageClient = createLanguageClient(worker);
        languageClient.start();

        return () => {
            languageClient?.stop();
            editor?.dispose();
            model.dispose();
            worker?.terminate();

            languageClient = null;
            editor = null;
            worker = null;
        };
    });

    $effect(() => {
        if (!editor) {
            return;
        }

        if (value !== editor.getValue()) {
            editor.setValue(value);
        }
    });

    $effect(() => {
        editor?.updateOptions({ readOnly });
    });
</script>

<div class="query-editor" style={`height: ${height}`} bind:this={containerEl}></div>

<style>
    .query-editor {
        width: 100%;
        border: 1px solid rgb(60 60 60);
        border-radius: 0.5rem;
        overflow: hidden;
    }
</style>
