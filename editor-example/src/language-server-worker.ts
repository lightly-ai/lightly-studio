import {
    BrowserMessageReader,
    BrowserMessageWriter,
    createConnection
} from 'vscode-languageserver/browser.js';
import { startLanguageServer } from 'langium/lsp';
import { createHelloLangServices } from './language/hello-lang-module.js';
import { EmptyFileSystem } from 'langium';

/* Create a connection using browser-compatible message reader/writer */
const messageReader = new BrowserMessageReader(self);
const messageWriter = new BrowserMessageWriter(self);
const connection = createConnection(messageReader, messageWriter);

/* Create Langium services for HelloLang */
const { shared } = createHelloLangServices({ connection, ...EmptyFileSystem });

/* Start the language server with the connection */
startLanguageServer(shared);
