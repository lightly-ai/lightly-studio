import * as monaco from 'monaco-editor';
import { MonacoLanguageClient } from 'monaco-languageclient';
import {
    CloseAction,
    ErrorAction
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

monaco.languages.setLanguageConfiguration('lightly-query', {
    comments: {
        lineComment: '#',
        blockComment: ['/*', '*/']
    },
    autoClosingPairs: [
        { open: '(', close: ')' },
        { open: '[', close: ']' },
        { open: '"', close: '"' },
        { open: '\'', close: '\'' }
    ],
    surroundingPairs: [
        { open: '(', close: ')' },
        { open: '[', close: ']' },
        { open: '"', close: '"' },
        { open: '\'', close: '\'' }
    ],
    brackets: [
        ['(', ')'],
        ['[', ']']
    ]
});

monaco.languages.setMonarchTokensProvider('lightly-query', {
    keywords: ['AND', 'OR', 'NOT', 'is', 'in', 'not'],
    typeKeywords: ['ImageSampleField', 'VideoSampleField', 'SampleField'],
    methodKeywords: [
        'contains', 'startswith', 'endswith', 'exists',
        'is_null', 'is_not_null', 'not_in', 'matches', 'icontains'
    ],
    literalKeywords: ['true', 'false', 'True', 'False', 'null', 'None', 'NULL'],
    dateFunctions: ['date', 'datetime', 'timestamp'],
    operators: ['==', '!=', '<=', '>=', '<', '>', '='],
    tokenizer: {
        root: [
            [/#[^\n\r]*/, 'comment'],
            [/\/\/[^\n\r]*/, 'comment'],
            [/\/\*/, 'comment', '@comment'],
            [/"([^"\\]|\\.)*$/, 'string.invalid'],
            [/'([^'\\]|\\.)*$/, 'string.invalid'],
            [/"/, 'string', '@doubleQuotedString'],
            [/'/, 'string', '@singleQuotedString'],
            [/\b(?:AND|OR|NOT)\b/, 'keyword'],
            [/\b(?:is|in|not)\b/, 'keyword.operator'],
            [/\b(?:ImageSampleField|VideoSampleField|SampleField)\b/, 'type.identifier'],
            [/\b(?:contains|startswith|endswith|exists|is_null|is_not_null|not_in|matches|icontains)\b/, 'predefined.function'],
            [/\b(?:date|datetime|timestamp)(?=\()/, 'predefined.function'],
            [/\b(?:true|false|True|False|null|None|NULL)\b/, 'constant.language'],
            [/-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/, 'number'],
            [/[a-zA-Z_]\w*/, 'identifier'],
            [/==|!=|<=|>=|=|<|>/, 'operator'],
            [/[()[\]]/, '@brackets'],
            [/\./, 'delimiter'],
            [/,/, 'delimiter'],
            [/\s+/, 'white']
        ],
        comment: [
            [/[^/*]+/, 'comment'],
            [/\*\//, 'comment', '@pop'],
            [/[/\*]/, 'comment']
        ],
        doubleQuotedString: [
            [/[^\\"]+/, 'string'],
            [/\\./, 'string.escape'],
            [/"/, 'string', '@pop']
        ],
        singleQuotedString: [
            [/[^\\']+/, 'string'],
            [/\\./, 'string.escape'],
            [/'/, 'string', '@pop']
        ]
    }
});

monaco.editor.defineTheme('lightly-query-theme', {
    base: 'vs-dark',
    inherit: true,
    rules: [
        { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
        { token: 'keyword', foreground: 'C586C0', fontStyle: 'bold' },
        { token: 'keyword.operator', foreground: 'D19A66', fontStyle: 'bold' },
        { token: 'operator', foreground: '56B6C2' },
        { token: 'type.identifier', foreground: 'E5C07B' },
        { token: 'predefined.function', foreground: '61AFEF' },
        { token: 'constant.language', foreground: 'D19A66' },
        { token: 'number', foreground: 'B5CEA8' },
        { token: 'string', foreground: '98C379' },
        { token: 'delimiter', foreground: 'ABB2BF' },
        { token: 'identifier', foreground: 'D7DAE0' }
    ],
    colors: {
        'editor.background': '#11161f',
        'editorLineNumber.foreground': '#5c6370',
        'editorLineNumber.activeForeground': '#c8ccd4',
        'editor.selectionBackground': '#264f78',
        'editor.inactiveSelectionBackground': '#1f3652',
        'editorCursor.foreground': '#f8f8f2'
    }
});

type HoverDoc = {
    label: string;
    description: string;
    example?: string;
};

const hoverDocs = new Map<string, HoverDoc>([
    ['AND', {
        label: 'Logical AND',
        description: 'Both expressions must evaluate to true.',
        example: 'ImageSampleField.width > 1024 AND ImageSampleField.height > 768'
    }],
    ['OR', {
        label: 'Logical OR',
        description: 'At least one of the expressions must evaluate to true.',
        example: 'ImageSampleField.tags.contains("reviewed") OR ImageSampleField.tags.contains("approved")'
    }],
    ['NOT', {
        label: 'Logical NOT',
        description: 'Negates the expression inside parentheses.',
        example: 'NOT (ImageSampleField.tags.contains("archived"))'
    }],
    ['is', {
        label: 'Comparison operator: is',
        description: 'Compares a field to a value. Use with `not` for `is not`.',
        example: 'ImageSampleField.format is "png"'
    }],
    ['in', {
        label: 'Membership operator: in',
        description: 'Checks whether a value belongs to a list or set of values.',
        example: 'ImageSampleField.format in ["png", "jpeg"]'
    }],
    ['not', {
        label: 'Negation modifier',
        description: 'Used as `is not` or `not in` inside a field comparison.',
        example: 'ImageSampleField.format not in ["bmp", "gif"]'
    }],
    ['ImageSampleField', {
        label: 'Field type: ImageSampleField',
        description: 'Top-level image sample fields such as size, metadata, predictions, and tags.',
        example: 'ImageSampleField.width > 1920'
    }],
    ['VideoSampleField', {
        label: 'Field type: VideoSampleField',
        description: 'Top-level video sample fields used to query video metadata and annotations.',
        example: 'VideoSampleField.duration > 60'
    }],
    ['SampleField', {
        label: 'Field type: SampleField',
        description: 'Generic sample field namespace when the query is not image- or video-specific.',
        example: 'SampleField.created_at >= date("2024-01-01")'
    }],
    ['width', {
        label: 'Property: width',
        description: 'Image width in pixels. Use with comparison operators to filter by image dimensions.',
        example: 'ImageSampleField.width > 1920'
    }],
    ['height', {
        label: 'Property: height',
        description: 'Image height in pixels. Use with comparison operators to filter by image dimensions.',
        example: 'ImageSampleField.height <= 1080'
    }],
    ['contains', {
        label: 'Method: contains(...)',
        description: 'Checks whether the field contains the provided substring or value.',
        example: 'ImageSampleField.tags.contains("reviewed")'
    }],
    ['startswith', {
        label: 'Method: startswith(...)',
        description: 'Checks whether a string field starts with the given prefix.',
        example: 'ImageSampleField.filename.startswith("batch_")'
    }],
    ['endswith', {
        label: 'Method: endswith(...)',
        description: 'Checks whether a string field ends with the given suffix.',
        example: 'ImageSampleField.filename.endswith(".png")'
    }],
    ['exists', {
        label: 'Method: exists()',
        description: 'Checks whether a field or nested value is present.',
        example: 'ImageSampleField.metadata.exists()'
    }],
    ['is_null', {
        label: 'Method: is_null()',
        description: 'Checks whether a field value is null.',
        example: 'ImageSampleField.metadata.score.is_null()'
    }],
    ['is_not_null', {
        label: 'Method: is_not_null()',
        description: 'Checks whether a field value is present and not null.',
        example: 'ImageSampleField.metadata.score.is_not_null()'
    }],
    ['not_in', {
        label: 'Method: not_in(...)',
        description: 'Checks whether a value does not belong to the provided list.',
        example: 'ImageSampleField.label.not_in(["ignore", "background"])'
    }],
    ['matches', {
        label: 'Method: matches(...)',
        description: 'Matches a field against a pattern expression.',
        example: 'ImageSampleField.filename.matches("^frame_[0-9]+")'
    }],
    ['icontains', {
        label: 'Method: icontains(...)',
        description: 'Case-insensitive version of `contains(...)`.',
        example: 'ImageSampleField.filename.icontains("preview")'
    }],
    ['date', {
        label: 'Date constructor',
        description: 'Creates a date literal from a quoted string.',
        example: 'SampleField.created_at >= date("2024-01-01")'
    }],
    ['datetime', {
        label: 'Datetime constructor',
        description: 'Creates a datetime literal from a quoted string.',
        example: 'SampleField.updated_at < datetime("2024-01-01T12:00:00Z")'
    }],
    ['timestamp', {
        label: 'Timestamp constructor',
        description: 'Creates a timestamp literal from a numeric Unix timestamp.',
        example: 'SampleField.created_at >= timestamp(1711929600)'
    }],
    ['==', {
        label: 'Equality operator',
        description: 'Checks whether a field exactly equals a value.',
        example: 'ImageSampleField.format == "png"'
    }],
    ['!=', {
        label: 'Inequality operator',
        description: 'Checks whether a field differs from a value.',
        example: 'ImageSampleField.format != "png"'
    }],
    ['<', {
        label: 'Less-than operator',
        description: 'Checks whether a field is smaller than a value.',
        example: 'ImageSampleField.width < 1024'
    }],
    ['>', {
        label: 'Greater-than operator',
        description: 'Checks whether a field is greater than a value.',
        example: 'ImageSampleField.width > 1024'
    }],
    ['<=', {
        label: 'Less-than-or-equal operator',
        description: 'Checks whether a field is less than or equal to a value.',
        example: 'ImageSampleField.height <= 1080'
    }],
    ['>=', {
        label: 'Greater-than-or-equal operator',
        description: 'Checks whether a field is greater than or equal to a value.',
        example: 'ImageSampleField.confidence >= 0.95'
    }],
    ['=', {
        label: 'Assignment-style equality operator',
        description: 'Accepted equality alias in the query grammar.',
        example: 'ImageSampleField.format = "png"'
    }]
]);

function getHoverEntryAtPosition(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): { token: string; range: monaco.IRange } | undefined {
    const word = model.getWordAtPosition(position);
    if (word && hoverDocs.has(word.word)) {
        return {
            token: word.word,
            range: new monaco.Range(position.lineNumber, word.startColumn, position.lineNumber, word.endColumn)
        };
    }

    const lineContent = model.getLineContent(position.lineNumber);
    const operatorPattern = /==|!=|<=|>=|=|<|>/g;

    for (const match of lineContent.matchAll(operatorPattern)) {
        const token = match[0];
        const startColumn = (match.index ?? 0) + 1;
        const endColumn = startColumn + token.length;
        if (position.column >= startColumn && position.column <= endColumn && hoverDocs.has(token)) {
            return {
                token,
                range: new monaco.Range(position.lineNumber, startColumn, position.lineNumber, endColumn)
            };
        }
    }

    return undefined;
}

monaco.languages.registerHoverProvider('lightly-query', {
    provideHover(model, position) {
        const entry = getHoverEntryAtPosition(model, position);
        if (!entry) {
            return null;
        }

        const doc = hoverDocs.get(entry.token);
        if (!doc) {
            return null;
        }

        const contents: monaco.IMarkdownString[] = [
            { value: `**${doc.label}**` },
            { value: doc.description }
        ];

        if (doc.example) {
            contents.push({ value: `\`\`\`lql\n${doc.example}\n\`\`\`` });
        }

        return {
            range: entry.range,
            contents
        };
    }
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
    theme: 'lightly-query-theme',
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
