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
    ['tags', {
        label: 'Property: tags',
        description: 'List of tags associated with the sample. Use with contains() method to filter by tags.',
        example: 'ImageSampleField.tags.contains("reviewed")'
    }],
    ['metadata', {
        label: 'Property: metadata',
        description: 'Custom metadata fields stored with the sample. Access nested properties using dot notation.',
        example: 'ImageSampleField.metadata.confidence > 0.95'
    }],
    ['created_at', {
        label: 'Property: created_at',
        description: 'Timestamp when the sample was created. Use with date() constructor for comparisons.',
        example: 'SampleField.created_at >= date("2024-01-01")'
    }],
    ['file_name', {
        label: 'Property: file_name',
        description: 'Name of the file. Use with string methods like startswith() or endswith().',
        example: 'ImageSampleField.file_name.endswith(".png")'
    }],
    ['format', {
        label: 'Property: format',
        description: 'File format (e.g., "png", "jpeg", "webp").',
        example: 'ImageSampleField.format == "png"'
    }],
    ['predictions', {
        label: 'Property: predictions',
        description: 'Array of model predictions for this sample. Access individual predictions using array indexing (e.g., predictions[0]). Each prediction typically has label, confidence, and bbox properties.',
        example: 'ImageSampleField.predictions[0].label == "cat"'
    }],
    ['duration', {
        label: 'Property: duration',
        description: 'Video duration in seconds.',
        example: 'VideoSampleField.duration > 60'
    }],
    ['fps', {
        label: 'Property: fps',
        description: 'Video frames per second.',
        example: 'VideoSampleField.fps == 30'
    }],
    ['label', {
        label: 'Property: label',
        description: 'Classification or detection label/class name. For predictions, use predictions[N].label to access the label of the Nth prediction.',
        example: 'ImageSampleField.predictions[0].label == "cat"'
    }],
    ['confidence', {
        label: 'Property: confidence',
        description: 'Prediction confidence score (0.0 to 1.0). Higher values indicate higher model confidence.',
        example: 'ImageSampleField.predictions[0].confidence > 0.95'
    }],
    ['bbox', {
        label: 'Property: bbox',
        description: 'Bounding box coordinates for object detections. Typically has x, y, width, height properties.',
        example: 'ImageSampleField.predictions[0].bbox.width > 100'
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

// Hardcoded tags for autocomplete (in production, fetch from API)
const availableTags = [
    'reviewed',
    'needs-labeling',
    'approved',
    'rejected',
    'high-quality',
    'low-quality',
    'duplicate',
    'archived',
    'test',
    'validation',
    'training'
];

// Hardcoded labels for autocomplete (in production, fetch from API)
const availableLabels = [
    'cat',
    'dog',
    'person',
    'car',
    'bicycle',
    'motorcycle',
    'airplane',
    'bus',
    'train',
    'truck',
    'bird',
    'horse',
    'sheep',
    'cow',
    'elephant',
    'bear',
    'zebra',
    'giraffe'
];

/**
 * Tag Completion Provider
 * 
 * Provides autocomplete suggestions for tags when user types: tags.contains("
 * 
 * To fetch tags dynamically from your API:
 * 1. Replace hardcoded `availableTags` array with an async fetch call
 * 2. Example API integration:
 * 
 *    let cachedTags: string[] = [];
 *    
 *    async function fetchAvailableTags(): Promise<string[]> {
 *        try {
 *            const response = await fetch('/api/datasets/tags');
 *            const data = await response.json();
 *            cachedTags = data.tags;
 *            return cachedTags;
 *        } catch (error) {
 *            console.error('Failed to fetch tags:', error);
 *            return cachedTags; // fallback to cache
 *        }
 *    }
 *    
 *    // Refresh tags periodically
 *    setInterval(() => fetchAvailableTags(), 60000); // every 60s
 *    
 * 3. In provideCompletionItems, use the fetched tags instead
 */
monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['"', "'"],
    
    provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        // Check if we're inside tags.contains(" or tags.contains('
        const tagsContainsMatch = textUntilPosition.match(/tags\.contains\(["']$/);
        
        if (tagsContainsMatch) {
            const wordInfo = model.getWordUntilPosition(position);
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: wordInfo.startColumn,
                endColumn: wordInfo.endColumn
            };
            
            const suggestions: monaco.languages.CompletionItem[] = availableTags.map(tag => ({
                label: tag,
                kind: monaco.languages.CompletionItemKind.Value,
                detail: 'Available tag',
                documentation: `Filter samples with tag: "${tag}"`,
                insertText: tag,
                range: range
            }));
            
            return { suggestions };
        }
        
        return { suggestions: [] };
    }
});

/**
 * Prediction Label Completion Provider
 * 
 * Provides autocomplete suggestions for prediction labels when user types:
 * - ImageSampleField.predictions[0].label == "
 * - predictions[1].label == "
 * 
 * To fetch labels dynamically from your API (similar to tags):
 * 1. Replace hardcoded `availableLabels` array with an async fetch call
 * 2. Example: fetch('/api/datasets/labels') or fetch('/api/models/classes')
 * 3. Can be model-specific or dataset-specific
 */
monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['"', "'"],
    
    provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        // Check if we're inside predictions[N].label == " or predictions[N].label == '
        // Supports: predictions[0].label, predictions[1].label, etc.
        const labelMatch = textUntilPosition.match(/predictions\[\d+\]\.label\s*(==|!=)\s*["']$/);
        
        if (labelMatch) {
            const wordInfo = model.getWordUntilPosition(position);
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: wordInfo.startColumn,
                endColumn: wordInfo.endColumn
            };
            
            const suggestions: monaco.languages.CompletionItem[] = availableLabels.map(label => ({
                label: label,
                kind: monaco.languages.CompletionItemKind.EnumMember,
                detail: 'Object class',
                documentation: `Filter predictions with label: "${label}"`,
                insertText: label,
                range: range
            }));
            
            return { suggestions };
        }
        
        return { suggestions: [] };
    }
});

/**
 * Field Property Completion Provider
 * 
 * Provides autocomplete for properties after typing:
 * - ImageSampleField. -> width, height, tags, metadata, etc.
 * - VideoSampleField. -> duration, fps, width, height, etc.
 * - SampleField. -> created_at, etc.
 */

interface FieldPropertyInfo {
    label: string;
    detail: string;
    documentation: string;
    insertText?: string;
}

const imageSampleFieldProperties: FieldPropertyInfo[] = [
    {
        label: 'width',
        detail: 'number',
        documentation: 'Image width in pixels',
        insertText: 'width'
    },
    {
        label: 'height',
        detail: 'number',
        documentation: 'Image height in pixels',
        insertText: 'height'
    },
    {
        label: 'tags',
        detail: 'list',
        documentation: 'Tags associated with the image sample',
        insertText: 'tags'
    },
    {
        label: 'metadata',
        detail: 'object',
        documentation: 'Custom metadata fields',
        insertText: 'metadata'
    },
    {
        label: 'created_at',
        detail: 'datetime',
        documentation: 'Timestamp when the sample was created',
        insertText: 'created_at'
    },
    {
        label: 'file_name',
        detail: 'string',
        documentation: 'Name of the image file',
        insertText: 'file_name'
    },
    {
        label: 'file_size',
        detail: 'number',
        documentation: 'Size of the file in bytes',
        insertText: 'file_size'
    },
    {
        label: 'format',
        detail: 'string',
        documentation: 'Image format (e.g., "png", "jpeg")',
        insertText: 'format'
    },
    {
        label: 'predictions',
        detail: 'list',
        documentation: 'Array of model predictions. Each prediction has properties like label, confidence, and bbox. Access using array indexing: predictions[0].label',
        insertText: 'predictions'
    },
    {
        label: 'text_similarity',
        detail: 'method',
        documentation: 'Calculate text similarity score',
        insertText: 'text_similarity("${1:query}")'
    }
];

const videoSampleFieldProperties: FieldPropertyInfo[] = [
    {
        label: 'duration',
        detail: 'number',
        documentation: 'Video duration in seconds',
        insertText: 'duration'
    },
    {
        label: 'fps',
        detail: 'number',
        documentation: 'Frames per second',
        insertText: 'fps'
    },
    {
        label: 'width',
        detail: 'number',
        documentation: 'Video width in pixels',
        insertText: 'width'
    },
    {
        label: 'height',
        detail: 'number',
        documentation: 'Video height in pixels',
        insertText: 'height'
    },
    {
        label: 'frame_count',
        detail: 'number',
        documentation: 'Total number of frames',
        insertText: 'frame_count'
    },
    {
        label: 'created_at',
        detail: 'datetime',
        documentation: 'Timestamp when the sample was created',
        insertText: 'created_at'
    },
    {
        label: 'tags',
        detail: 'list',
        documentation: 'Tags associated with the video sample',
        insertText: 'tags'
    }
];

const sampleFieldProperties: FieldPropertyInfo[] = [
    {
        label: 'created_at',
        detail: 'datetime',
        documentation: 'Timestamp when the sample was created',
        insertText: 'created_at'
    },
    {
        label: 'updated_at',
        detail: 'datetime',
        documentation: 'Timestamp when the sample was last updated',
        insertText: 'updated_at'
    },
    {
        label: 'tags',
        detail: 'list',
        documentation: 'Tags associated with the sample',
        insertText: 'tags'
    }
];

monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['.'],
    
    provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        let properties: FieldPropertyInfo[] = [];
        
        // Check which field type was typed
        if (textUntilPosition.match(/ImageSampleField\.$/)) {
            properties = imageSampleFieldProperties;
        } else if (textUntilPosition.match(/VideoSampleField\.$/)) {
            properties = videoSampleFieldProperties;
        } else if (textUntilPosition.match(/SampleField\.$/)) {
            properties = sampleFieldProperties;
        } else {
            return { suggestions: [] };
        }
        
        const wordInfo = model.getWordUntilPosition(position);
        const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: wordInfo.startColumn,
            endColumn: wordInfo.endColumn
        };
        
        const suggestions: monaco.languages.CompletionItem[] = properties.map(prop => ({
            label: prop.label,
            kind: prop.detail === 'method' 
                ? monaco.languages.CompletionItemKind.Method 
                : monaco.languages.CompletionItemKind.Property,
            detail: prop.detail,
            documentation: prop.documentation,
            insertText: prop.insertText || prop.label,
            insertTextRules: prop.insertText?.includes('${') 
                ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet 
                : undefined,
            range: range
        }));
        
        return { suggestions };
    }
});

/**
 * Tag Methods Completion Provider
 * 
 * Provides autocomplete for methods when typing after tags property:
 * - ImageSampleField.tags. -> contains()
 * - VideoSampleField.tags. -> contains()
 * - SampleField.tags. -> contains()
 */

const tagMethods: FieldPropertyInfo[] = [
    {
        label: 'contains',
        detail: 'method',
        documentation: 'Check if the tag list contains a specific value. Returns true if the tag exists.',
        insertText: 'contains("${1:tag-name}")'
    },
    {
        label: 'startswith',
        detail: 'method',
        documentation: 'Check if any tag starts with the given prefix.',
        insertText: 'startswith("${1:prefix}")'
    },
    {
        label: 'endswith',
        detail: 'method',
        documentation: 'Check if any tag ends with the given suffix.',
        insertText: 'endswith("${1:suffix}")'
    },
    {
        label: 'exists',
        detail: 'method',
        documentation: 'Check if the tags field exists and is not empty.',
        insertText: 'exists()'
    },
    {
        label: 'is_null',
        detail: 'method',
        documentation: 'Check if the tags field is null or undefined.',
        insertText: 'is_null()'
    },
    {
        label: 'is_not_null',
        detail: 'method',
        documentation: 'Check if the tags field exists and is not null.',
        insertText: 'is_not_null()'
    }
];

monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['.'],
    
    provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        // Check if we're after .tags.
        const tagsMethodMatch = textUntilPosition.match(/\b(ImageSampleField|VideoSampleField|SampleField)\.tags\.$/);
        
        if (!tagsMethodMatch) {
            return { suggestions: [] };
        }
        
        const wordInfo = model.getWordUntilPosition(position);
        const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: wordInfo.startColumn,
            endColumn: wordInfo.endColumn
        };
        
        const suggestions: monaco.languages.CompletionItem[] = tagMethods.map(method => ({
            label: method.label,
            kind: monaco.languages.CompletionItemKind.Method,
            detail: method.detail,
            documentation: method.documentation,
            insertText: method.insertText || method.label,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: range
        }));
        
        return { suggestions };
    }
});

/**
 * String Field Methods Completion Provider
 * 
 * Provides autocomplete for string methods on fields like:
 * - ImageSampleField.file_name. -> startswith(), endswith(), contains(), matches()
 * - ImageSampleField.format. -> string comparison methods
 */

const stringMethods: FieldPropertyInfo[] = [
    {
        label: 'startswith',
        detail: 'method',
        documentation: 'Check if the string starts with the given prefix.',
        insertText: 'startswith("${1:prefix}")'
    },
    {
        label: 'endswith',
        detail: 'method',
        documentation: 'Check if the string ends with the given suffix.',
        insertText: 'endswith("${1:suffix}")'
    },
    {
        label: 'contains',
        detail: 'method',
        documentation: 'Check if the string contains the given substring.',
        insertText: 'contains("${1:substring}")'
    },
    {
        label: 'icontains',
        detail: 'method',
        documentation: 'Case-insensitive version of contains().',
        insertText: 'icontains("${1:substring}")'
    },
    {
        label: 'matches',
        detail: 'method',
        documentation: 'Check if the string matches a regular expression pattern.',
        insertText: 'matches("${1:pattern}")'
    },
    {
        label: 'is_null',
        detail: 'method',
        documentation: 'Check if the field is null or undefined.',
        insertText: 'is_null()'
    },
    {
        label: 'is_not_null',
        detail: 'method',
        documentation: 'Check if the field exists and is not null.',
        insertText: 'is_not_null()'
    }
];

monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['.'],
    
    provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        // Check if we're after a string field property
        const stringFieldMatch = textUntilPosition.match(/\b(ImageSampleField|VideoSampleField|SampleField)\.(file_name|format)\.$/);
        
        if (!stringFieldMatch) {
            return { suggestions: [] };
        }
        
        const wordInfo = model.getWordUntilPosition(position);
        const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: wordInfo.startColumn,
            endColumn: wordInfo.endColumn
        };
        
        const suggestions: monaco.languages.CompletionItem[] = stringMethods.map(method => ({
            label: method.label,
            kind: monaco.languages.CompletionItemKind.Method,
            detail: method.detail,
            documentation: method.documentation,
            insertText: method.insertText || method.label,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: range
        }));
        
        return { suggestions };
    }
});

/**
 * Comparison Operator Completion Provider
 * 
 * Provides autocomplete for comparison operators when user types space after a property:
 * - ImageSampleField.width [space] -> suggests >, <, >=, <=, ==, !=
 * - ImageSampleField.metadata.confidence [space] -> suggests comparison operators
 * - predictions[0].label [space] -> suggests ==, !=
 */

interface OperatorSuggestion {
    label: string;
    detail: string;
    documentation: string;
    insertText: string;
    sortText?: string;
}

const comparisonOperators: OperatorSuggestion[] = [
    {
        label: '==',
        detail: 'Equal to',
        documentation: 'Check if the field value equals the specified value. Returns true when values are exactly the same.',
        insertText: '== ${1:value}',
        sortText: '1'
    },
    {
        label: '!=',
        detail: 'Not equal to',
        documentation: 'Check if the field value does not equal the specified value. Returns true when values differ.',
        insertText: '!= ${1:value}',
        sortText: '2'
    },
    {
        label: '>',
        detail: 'Greater than',
        documentation: 'Check if the field value is greater than the specified value. Use for numeric comparisons.',
        insertText: '> ${1:number}',
        sortText: '3'
    },
    {
        label: '<',
        detail: 'Less than',
        documentation: 'Check if the field value is less than the specified value. Use for numeric comparisons.',
        insertText: '< ${1:number}',
        sortText: '4'
    },
    {
        label: '>=',
        detail: 'Greater than or equal to',
        documentation: 'Check if the field value is greater than or equal to the specified value. Inclusive comparison for numeric fields.',
        insertText: '>= ${1:number}',
        sortText: '5'
    },
    {
        label: '<=',
        detail: 'Less than or equal to',
        documentation: 'Check if the field value is less than or equal to the specified value. Inclusive comparison for numeric fields.',
        insertText: '<= ${1:number}',
        sortText: '6'
    }
];

monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: [' '],
    
    provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        // Check if we just typed a space after a property or nested field
        // Matches patterns like:
        // - ImageSampleField.width 
        // - ImageSampleField.metadata.confidence 
        // - predictions[0].confidence 
        // - SampleField.created_at 
        const propertyMatch = textUntilPosition.match(/\b(ImageSampleField|VideoSampleField|SampleField|predictions\[\d+\])\.[\w.]+\s$/);
        
        if (!propertyMatch) {
            return { suggestions: [] };
        }
        
        const wordInfo = model.getWordUntilPosition(position);
        const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: wordInfo.startColumn,
            endColumn: wordInfo.endColumn
        };
        
        const suggestions: monaco.languages.CompletionItem[] = comparisonOperators.map(op => ({
            label: op.label,
            kind: monaco.languages.CompletionItemKind.Operator,
            detail: op.detail,
            documentation: op.documentation,
            insertText: op.insertText,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            sortText: op.sortText,
            range: range
        }));
        
        return { suggestions };
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
