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
        if (label === 'lightly-query') {
            return new Worker(new URL('./language-server-worker.ts', import.meta.url), { type: 'module' });
        }
        return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url), { type: 'module' });
    }
};

// Register Lightly Query Language
monaco.languages.register({
    id: 'lightly-query',
    extensions: ['.lql', '.lightlyql'],
    aliases: ['LightlyQuery', 'lightly-query', 'LQL'],
    mimetypes: ['text/lightly-query']
});

// Create the editor with Lightly Query Language examples
const editor = monaco.editor.create(document.getElementById('editor')!, {
    value: `# Lightly Query Language Examples
# Query syntax for dataset.match() function

# Simple field comparisons
ImageSampleField.width > 1920
ImageSampleField.height <= 1080
ImageSampleField.tags.contains("reviewed")

# Complex boolean queries
(ImageSampleField.width < 500 AND NOT (ImageSampleField.tags.contains("reviewed"))) OR ImageSampleField.tags.contains("needs-labeling")

# Metadata queries
ImageSampleField.metadata.confidence > 0.95
ImageSampleField.predictions[0].label == "cat"

# Video queries
VideoSampleField.duration > 60 AND VideoSampleField.fps == 30
`,
    language: 'lightly-query',
    theme: 'vs-dark',
    automaticLayout: true
});

// Create language client
function createLanguageClient(worker: Worker): MonacoLanguageClient {
    const reader = new BrowserMessageReader(worker);
    const writer = new BrowserMessageWriter(worker);
    
    return new MonacoLanguageClient({
        name: 'Langium Language Client',
        clientOptions: {
            documentSelector: [
                { language: 'lightly-query' }
            ],
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

console.log('Monaco Editor with Langium LSP is ready for LightlyQuery.');
