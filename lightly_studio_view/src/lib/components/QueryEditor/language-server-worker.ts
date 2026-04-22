// Entry point for the LightlyQuery language server, executed inside a dedicated
// Web Worker so parsing, validation, and LSP traffic stay off the UI thread.

import {
    BrowserMessageReader,
    BrowserMessageWriter,
    createConnection
} from 'vscode-languageserver/browser.js';
import { EmptyFileSystem } from 'langium';
import { startLanguageServer } from 'langium/lsp';
import { createLightlyQueryServices } from './language/lightly-query-module.js';

// LSP normally speaks over stdio; in the browser we bridge it to the worker's
// postMessage channel. `self` is the worker's own global, which the host page
// talks to via `worker.postMessage` / `worker.onmessage`.
const connection = createConnection(new BrowserMessageReader(self), new BrowserMessageWriter(self));

// Langium services expect a file system. Browsers don't have one, so we inject
// the in-memory `EmptyFileSystem` — documents live only as LSP text buffers.
const shared = createLightlyQueryServices({ connection, ...EmptyFileSystem });

// Wires the Langium services to the LSP connection and begins listening for
// requests from the MonacoLanguageClient on the main thread.
startLanguageServer(shared);
