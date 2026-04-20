import {
    BrowserMessageReader,
    BrowserMessageWriter,
    createConnection
} from 'vscode-languageserver/browser.js';
import { startLanguageServer } from 'langium/lsp';
import { createLightlyQueryServices } from './language/lightly-query-module.js';
import { EmptyFileSystem } from 'langium';

/* Create a connection using browser-compatible message reader/writer */
const messageReader = new BrowserMessageReader(self);
const messageWriter = new BrowserMessageWriter(self);
const connection = createConnection(messageReader, messageWriter);

/* Create Langium services for both languages */
const context = { connection, ...EmptyFileSystem };
const lightlyQueryServices = createLightlyQueryServices(context);

/* Use the shared services from one of them (they're the same) */
const { shared } = lightlyQueryServices;

/* Start the language server with the connection */
startLanguageServer(shared);
