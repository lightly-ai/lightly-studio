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
        if (label === 'dataset-query') {
            return new Worker(new URL('./language-server-worker.ts', import.meta.url), { type: 'module' });
        }
        return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url), { type: 'module' });
    }
};

// Register DatasetQuery language
monaco.languages.register({
    id: 'dataset-query',
    extensions: ['.py'],
    aliases: ['DatasetQuery', 'dataset-query', 'Python'],
    mimetypes: ['text/x-python']
});

// Create the editor
const editor = monaco.editor.create(document.getElementById('editor')!, {
    value: `# Welcome to Dataset Query Language!
# Write Python dataset queries with LSP support

# Basic annotation query - find images with cats
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
)

# Logical AND - find images with exactly 1 cat and 1 dog
dataset.query().match(
    AND(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat") == 1,
        ObjectDetectionQuery.count(ObjectDetectionField.label == "dog") == 1
    )
)

# Query with metadata - cats in large images
dataset.query().match(
    AND(
        ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
        ImageSampleField.width > 500
    )
)

# With sorting - sort by cat count descending
dataset.query().match(
    AND(
        ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
        ImageSampleField.width > 500
    )
).order_by(
    OrderByField(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat")
    ).desc()
)
`,
    language: 'dataset-query',
    theme: 'vs-dark',
    automaticLayout: true,
    minimap: { enabled: false },
    lineNumbers: 'on',
    fontSize: 13,
    // Enable autocomplete and hover features
    suggestOnTriggerCharacters: true,
    quickSuggestions: {
        other: true,
        comments: false,
        strings: false
    },
    suggest: {
        showMethods: true,
        showFunctions: true,
        showKeywords: true,
        showProperties: true,
        snippetsPreventQuickSuggestions: false
    },
    parameterHints: {
        enabled: true
    },
    hover: {
        enabled: true,
        delay: 300
    }
});

// Create language client
function createLanguageClient(worker: Worker): MonacoLanguageClient {
    const reader = new BrowserMessageReader(worker);
    const writer = new BrowserMessageWriter(worker);
    
    return new MonacoLanguageClient({
        name: 'DatasetQuery Language Client',
        clientOptions: {
            documentSelector: [{ language: 'dataset-query' }],
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

console.log('DatasetQuery Monaco Editor with Langium LSP is ready!');
