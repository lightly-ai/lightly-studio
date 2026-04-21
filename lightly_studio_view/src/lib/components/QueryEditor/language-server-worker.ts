import {
    BrowserMessageReader,
    BrowserMessageWriter,
    createConnection
} from 'vscode-languageserver/browser.js';
import { EmptyFileSystem } from 'langium';
import { startLanguageServer } from 'langium/lsp';
import { createLightlyQueryServices } from './language/lightly-query-module.js';

const messageReader = new BrowserMessageReader(self);
const messageWriter = new BrowserMessageWriter(self);
const connection = createConnection(messageReader, messageWriter);

const context = { connection, ...EmptyFileSystem };
const lightlyQueryServices = createLightlyQueryServices(context);
const { shared } = lightlyQueryServices;

startLanguageServer(shared);
