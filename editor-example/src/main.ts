import * as monaco from 'monaco-editor';
import { MonacoLanguageClient } from 'monaco-languageclient';
import {
    CloseAction,
    ErrorAction,
    MessageTransports
} from 'vscode-languageclient';
import {
    toSocket,
    WebSocketMessageReader,
    WebSocketMessageWriter
} from 'vscode-languageclient';
import { BrowserMessageReader, BrowserMessageWriter } from 'vscode-languageserver-protocol/browser.js';

// Configure Monaco environment
self.MonacoEnvironment = {
    getWorker(_: string, label: string) {
        if (label === 'hello-lang') {
            return new Worker(new URL('./language-server-worker.ts', import.meta.url), { type: 'module' });
        }
        return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url), { type: 'module' });
    }
};

// Register HelloLang language
monaco.languages.register({
    id: 'hello-lang',
    extensions: ['.hello'],
    aliases: ['HelloLang', 'hello-lang'],
    mimetypes: ['text/hello-lang']
});

// Create the editor
const editor = monaco.editor.create(document.getElementById('editor')!, {
    value: `// Welcome to HelloLang!
// Type "hello" followed by a name.
// Try:
hello World!
hello Alice.
hello bob!
`,
    language: 'hello-lang',
    theme: 'vs-dark',
    automaticLayout: true
});

// Create language client
function createLanguageClient(worker: Worker): MonacoLanguageClient {
    const reader = new BrowserMessageReader(worker);
    const writer = new BrowserMessageWriter(worker);
    
    return new MonacoLanguageClient({
        name: 'HelloLang Language Client',
        clientOptions: {
            documentSelector: [{ language: 'hello-lang' }],
            errorHandler: {
                error: () => ({ action: ErrorAction.Continue }),
                closed: () => ({ action: CloseAction.DoNotRestart })
            }
        },
        connectionProvider: {
            get: () => {
                return Promise.resolve({ reader, writer });
            }
        }
    });
}

// Start the language client
const worker = new Worker(new URL('./language-server-worker.ts', import.meta.url), { type: 'module' });
const client = createLanguageClient(worker);
client.start();

console.log('HelloLang Monaco Editor with Langium LSP is ready!');
