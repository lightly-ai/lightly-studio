// One-time initialization of the VSCode API services that `monaco-languageclient`
// depends on. `MonacoLanguageClient` extends `BaseLanguageClient` from
// `vscode-languageclient/browser`, which reaches for a `vscode` API that only
// exists after `@codingame/monaco-vscode-api`'s `initialize(...)` has run —
// constructing the client before that throws "Default api is not ready yet".
//
// The wrapper's `start()` is itself guarded against double-initialization, but
// we memoize the promise so concurrent editor mounts share a single startup.

import { LogLevel } from '@codingame/monaco-vscode-api';
import { MonacoVscodeApiWrapper } from 'monaco-languageclient/vscodeApiWrapper';

let startupPromise: Promise<void> | null = null;

export function ensureMonacoVscodeServices(): Promise<void> {
    if (!startupPromise) {
        const wrapper = new MonacoVscodeApiWrapper({
            // `classic` keeps the Monarch tokenizer path — matches the
            // `setMonarchTokensProvider` call in `monaco-lightly-query.ts`.
            // `extended` would switch to TextMate grammars and pull in a much
            // larger dependency graph.
            $type: 'classic',
            viewsConfig: { $type: 'EditorService' },
            logLevel: LogLevel.Warning
        });
        startupPromise = wrapper.start({ caller: 'LightlyQueryEditor' });
    }
    return startupPromise;
}
