import * as monaco from 'monaco-editor';

const LIGHTLY_QUERY_LANGUAGE_ID = 'lightly-query';
const LIGHTLY_QUERY_THEME_ID = 'lightly-query-theme';

let isRegistered = false;

export const LIGHTLY_QUERY_DEFAULT_VALUE = `# Lightly Query examples
ImageSampleField.width > 1920
ImageSampleField.tags.contains("reviewed")
VideoSampleField.duration > 60
`;

function createEditorWorker(): Worker {
    return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url), {
        type: 'module'
    });
}

function createLanguageServerWorker(): Worker {
    return new Worker(new URL('./language-server-worker.ts', import.meta.url), { type: 'module' });
}

export function createLightlyQueryLanguageServerWorker(): Worker {
    return createLanguageServerWorker();
}

export function registerLightlyQueryMonacoLanguage(): void {
    if (isRegistered) {
        return;
    }

    const globalScope = globalThis as typeof globalThis & {
        MonacoEnvironment?: {
            getWorker: (_moduleId: string, label: string) => Worker;
        };
    };

    globalScope.MonacoEnvironment = {
        getWorker: (_moduleId: string, label: string): Worker => {
            if (label === LIGHTLY_QUERY_LANGUAGE_ID) {
                return createLanguageServerWorker();
            }
            return createEditorWorker();
        }
    };

    monaco.languages.register({
        id: LIGHTLY_QUERY_LANGUAGE_ID,
        extensions: ['.lql', '.lightlyql'],
        aliases: ['LightlyQuery', 'lightly-query', 'LQL'],
        mimetypes: ['text/lightly-query']
    });

    monaco.languages.setLanguageConfiguration(LIGHTLY_QUERY_LANGUAGE_ID, {
        comments: {
            lineComment: '#',
            blockComment: ['/*', '*/']
        },
        autoClosingPairs: [
            { open: '(', close: ')' },
            { open: '[', close: ']' },
            { open: '"', close: '"' },
            { open: "'", close: "'" }
        ],
        surroundingPairs: [
            { open: '(', close: ')' },
            { open: '[', close: ']' },
            { open: '"', close: '"' },
            { open: "'", close: "'" }
        ],
        brackets: [
            ['(', ')'],
            ['[', ']']
        ]
    });

    monaco.languages.setMonarchTokensProvider(LIGHTLY_QUERY_LANGUAGE_ID, {
        tokenizer: {
            root: [
                [/#[^\n\r]*/, 'comment'],
                [/"([^"\\]|\\.)*$/, 'string.invalid'],
                [/'([^'\\]|\\.)*$/, 'string.invalid'],
                [/"/, 'string', '@doubleQuotedString'],
                [/'/, 'string', '@singleQuotedString'],
                [/\b(?:AND|OR|NOT)\b/, 'keyword'],
                [/\b(?:is|in|not)\b/, 'keyword.operator'],
                [/\b(?:true|false|True|False|null|None|NULL)\b/, 'constant.language'],
                [/\b(?:ImageSampleField|VideoSampleField|SampleField)\b/, 'type.identifier'],
                [/-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/, 'number'],
                [/[a-zA-Z_]\w*/, 'identifier'],
                [/==|!=|<=|>=|=|<|>/, 'operator'],
                [/[()[\]]/, '@brackets'],
                [/\./, 'delimiter'],
                [/,/, 'delimiter'],
                [/\s+/, 'white']
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

    monaco.editor.defineTheme(LIGHTLY_QUERY_THEME_ID, {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
            { token: 'keyword', foreground: 'C586C0', fontStyle: 'bold' },
            { token: 'keyword.operator', foreground: 'D19A66', fontStyle: 'bold' },
            { token: 'operator', foreground: '56B6C2' },
            { token: 'type.identifier', foreground: 'E5C07B' },
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

    isRegistered = true;
}

export { LIGHTLY_QUERY_LANGUAGE_ID, LIGHTLY_QUERY_THEME_ID };
