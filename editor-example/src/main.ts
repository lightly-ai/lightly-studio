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

monaco.languages.setMonarchTokensProvider('dataset-query', {
    keywords: [
        'dataset',
        'query',
        'match',
        'order_by',
        'AND',
        'OR',
        'NOT',
        'ObjectDetectionQuery',
        'ClassificationQuery',
        'InstanceSegmentationQuery',
        'ObjectDetectionField',
        'ClassificationField',
        'ImageSampleField',
        'OrderByField',
        'desc',
        'asc',
        'text_similarity'
    ],
    operators: ['==', '!=', '>=', '<=', '>', '<'],
    tokenizer: {
        root: [
            [/#.*$/, 'comment'],
            [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],
            [/\b\d+\b/, 'number'],
            [/[()]/, '@brackets'],
            [/[.,]/, 'delimiter'],
            [/@operators/, 'operator'],
            [/[a-zA-Z_][a-zA-Z0-9_]*/, {
                cases: {
                    '@keywords': 'keyword',
                    '@default': 'identifier'
                }
            }]
        ],
        string: [
            [/[^\\"]+/, 'string'],
            [/\\./, 'string.escape'],
            [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }]
        ]
    }
});

monaco.editor.defineTheme('dataset-query-theme', {
    base: 'vs-dark',
    inherit: true,
    rules: [
        { token: 'comment', foreground: '6A9955' },
        { token: 'keyword', foreground: '569CD6' },
        { token: 'identifier', foreground: 'D4D4D4' },
        { token: 'string', foreground: 'CE9178' },
        { token: 'number', foreground: 'B5CEA8' },
        { token: 'operator', foreground: 'D4D4D4' },
        { token: 'delimiter', foreground: 'D4D4D4' }
    ],
    colors: {
        'editor.background': '#1E1E1E'
    }
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
    theme: 'dataset-query-theme',
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
