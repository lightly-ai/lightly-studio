// LightlyQuery-specific editor composable. Layers the LSP worker and Monaco
// language client on top of `useMonacoEditor`, so the Svelte component only
// has to bind a container element and its props.
//
// Setup at a glance:
//   1. Register the language with Monaco (grammar ID, theme, tokenizer).
//   2. Delegate editor + model lifecycle to `useMonacoEditor`.
//   3. On mount: spin up the Langium LSP worker and connect a MonacoLanguageClient.
//   4. On destroy: wait for startup to settle, then stop the client and
//      terminate the worker.

import { MonacoLanguageClient } from 'monaco-languageclient';
import { CloseAction, ErrorAction } from 'vscode-languageclient';
import {
    BrowserMessageReader,
    BrowserMessageWriter
} from 'vscode-languageserver-protocol/browser.js';
import { onDestroy } from 'svelte';
import {
    LIGHTLY_QUERY_LANGUAGE_ID,
    LIGHTLY_QUERY_THEME_ID,
    registerLightlyQueryMonacoLanguage
} from './monaco-lightly-query.js';
import { ensureMonacoVscodeServices } from './monaco-vscode-services.js';
import { useMonacoEditor, type MonacoEditorHandle } from './useMonacoEditor.svelte.js';
import {
    QueryExprTranslationRequest,
    type QueryExprTranslationResult
} from './language/query-expr-translation.js';

export interface UseLightlyQueryEditorOptions {
    // Reactive getter for the editor's current text. Tracked inside a
    // `$effect`, so external writes to the underlying state push into the
    // editor (guarded against echoing the user's own keystrokes back).
    value: () => string;

    // Write-back callback invoked on every edit. The caller typically assigns
    // to its own `$bindable` prop here — this is the other half of two-way
    // value binding.
    onValueChange: (value: string) => void;

    // Reactive getter for the readOnly flag. Optional; defaults to false.
    // Tracked in a `$effect` so toggling it at runtime updates the editor.
    readOnly?: () => boolean;
}

export interface LightlyQueryEditorHandle extends MonacoEditorHandle {
    translateLightlyQuery: (value: string) => Promise<QueryExprTranslationResult | null>;
}

export function useLightlyQueryEditor(
    options: UseLightlyQueryEditorOptions
): LightlyQueryEditorHandle {
    // Safe to call on every mount — the function is idempotent.
    registerLightlyQueryMonacoLanguage();

    const editor = useMonacoEditor({
        language: LIGHTLY_QUERY_LANGUAGE_ID,
        theme: LIGHTLY_QUERY_THEME_ID,
        value: options.value,
        onValueChange: options.onValueChange,
        readOnly: options.readOnly
    });

    // LSP state kept outside `mount` so the `onDestroy` below can tear it
    // down. `startupPromise` lets destroy synchronize with an in-flight start.
    let lspWorker: Worker | null = null;
    let languageClient: MonacoLanguageClient | null = null;
    let startupPromise: Promise<void> | null = null;
    let isDestroyed = false;

    function mount(container: HTMLElement): void {
        // `MonacoLanguageClient`'s base class reaches for a `vscode` API that
        // only exists once `@codingame/monaco-vscode-api` is initialized, so
        // every editor mount funnels through a shared, memoized startup.
        startupPromise = ensureMonacoVscodeServices()
            .then(() => {
                if (isDestroyed) {
                    return;
                }

                editor.mount(container);

                // Spawn the Langium LSP worker and bridge it to the client via the
                // browser LSP message transport (postMessage under the hood).
                lspWorker = new Worker(new URL('./language-server-worker.ts', import.meta.url), {
                    type: 'module'
                });
                const reader = new BrowserMessageReader(lspWorker);
                const writer = new BrowserMessageWriter(lspWorker);

                // The language client provides validation, completion, and hover
                // to Monaco for documents matching the LightlyQuery language ID.
                // We keep the editor alive on transport errors (Continue) but do
                // not auto-restart a closed connection, since the worker won't
                // recover on its own after a hard failure.
                languageClient = new MonacoLanguageClient({
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

                return languageClient.start();
            })
            .catch((error) => {
                if (!isDestroyed) {
                    console.error('Failed to start LightlyQuery language client:', error);
                }
            });
    }

    async function translateLightlyQuery(
        value: string
    ): Promise<QueryExprTranslationResult | null> {
        await startupPromise;
        if (!languageClient || isDestroyed) {
            return null;
        }

        try {
            return await languageClient.sendRequest(QueryExprTranslationRequest, value);
        } catch (error) {
            console.error('Failed to translate LightlyQuery value:', error);
            return null;
        }
    }

    onDestroy(() => {
        // Snapshot references before nulling so the async teardown below
        // still sees them even after the component has detached.
        isDestroyed = true;
        const clientToStop = languageClient;
        const workerToTerminate = lspWorker;
        languageClient = null;
        lspWorker = null;

        // Wait for startup to settle before tearing down — stopping a client
        // mid-start leaves it in an inconsistent state that throws on `stop`.
        void startupPromise?.finally(async () => {
            try {
                await clientToStop?.stop();
            } catch (error) {
                console.error('Failed to stop LightlyQuery language client:', error);
            }
            workerToTerminate?.terminate();
        });
    });

    return { mount, translateLightlyQuery };
}
