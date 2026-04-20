import * as monaco from 'monaco-editor';

const sqlKeywords = [
    'SELECT',
    'FROM',
    'WHERE',
    'JOIN',
    'LEFT',
    'RIGHT',
    'INNER',
    'ON',
    'GROUP',
    'BY',
    'ORDER',
    'LIMIT',
    'AS',
    'AND',
    'OR',
    'NOT',
    'NULL',
    'LIKE',
    'IN',
    'DISTINCT',
    'ASC',
    'DESC'
];

const sqlFunctions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX'];
const sqlTables = ['users', 'orders', 'products'];
const sqlColumns = ['id', 'name', 'email', 'status', 'created_at', 'total_amount', 'user_id'];

const hoverDocs: Record<string, string> = {
    SELECT:
        '**SELECT**\n\nChoose which columns or expressions to return from a query.\n\n' +
        '```sql\nSELECT id, name\nFROM users;\n```',
    FROM:
        '**FROM**\n\nSpecify the source table or subquery.\n\n' +
        '```sql\nSELECT id\nFROM users;\n```',
    WHERE:
        '**WHERE**\n\nFilter rows before grouping or ordering.\n\n' +
        '```sql\nSELECT *\nFROM orders\nWHERE total_amount > 100;\n```',
    JOIN:
        '**JOIN**\n\nCombine rows from two tables using a matching condition.\n\n' +
        '```sql\nSELECT users.name, orders.total_amount\nFROM users\nJOIN orders ON users.id = orders.user_id;\n```',
    ORDER:
        '**ORDER BY**\n\nSort the result set by one or more columns.\n\n' +
        '```sql\nSELECT name\nFROM users\nORDER BY created_at DESC;\n```',
    GROUP:
        '**GROUP BY**\n\nGroup rows before applying aggregate functions like `COUNT` or `SUM`.\n\n' +
        '```sql\nSELECT status, COUNT(*)\nFROM users\nGROUP BY status;\n```',
    LIMIT:
        '**LIMIT**\n\nRestrict how many rows are returned.\n\n' +
        '```sql\nSELECT *\nFROM users\nLIMIT 10;\n```',
    COUNT:
        '**COUNT(...)**\n\nAggregate function that returns the number of rows or non-null values.\n\n' +
        '```sql\nSELECT COUNT(*)\nFROM users;\n```',
    users:
        '**users**\n\nExample table containing user records.\n\nColumns: `id`, `name`, `email`, `status`, `created_at`.',
    orders:
        '**orders**\n\nExample table containing purchase records.\n\nColumns: `id`, `user_id`, `total_amount`, `created_at`.',
    products:
        '**products**\n\nExample table containing catalog items.\n\nColumns: `id`, `name`, `status`.'
};

// Configure Monaco environment
self.MonacoEnvironment = {
    getWorker(_: string, label: string) {
        if (label === 'sql-demo') {
            return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url), {
                type: 'module'
            });
        }

        return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url), {
            type: 'module'
        });
    }
};

monaco.languages.register({
    id: 'sql-demo',
    extensions: ['.sql'],
    aliases: ['SQL Demo', 'sql-demo']
});

monaco.languages.setMonarchTokensProvider('sql-demo', {
    tokenizer: {
        root: [
            [/--.*$/, 'comment'],
            [/'/, { token: 'string.quote', bracket: '@open', next: '@string' }],
            [/\b\d+(\.\d+)?\b/, 'number'],
            [/[;,.]/, 'delimiter'],
            [/[()]/, '@brackets'],
            [/(<=|>=|<>|!=|=|<|>)/, 'operator'],
            [/[a-zA-Z_][\w$]*/, {
                cases: {
                    '@sqlFunctions': 'predefined',
                    '@sqlKeywords': 'keyword',
                    '@default': 'identifier'
                }
            }]
        ],
        string: [
            [/[^']+/, 'string'],
            [/''/, 'string.escape'],
            [/'/, { token: 'string.quote', bracket: '@close', next: '@pop' }]
        ]
    },
    sqlKeywords,
    sqlFunctions
});

monaco.editor.defineTheme('sql-demo-theme', {
    base: 'vs-dark',
    inherit: true,
    rules: [
        { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
        { token: 'keyword', foreground: '4FC1FF', fontStyle: 'bold' },
        { token: 'predefined', foreground: 'DCDCAA' },
        { token: 'identifier', foreground: 'D4D4D4' },
        { token: 'string', foreground: 'CE9178' },
        { token: 'number', foreground: 'B5CEA8' },
        { token: 'operator', foreground: 'C586C0' },
        { token: 'delimiter', foreground: 'D4D4D4' }
    ],
    colors: {
        'editor.background': '#111827',
        'editorLineNumber.foreground': '#4B5563',
        'editorLineNumber.activeForeground': '#9CA3AF',
        'editor.selectionBackground': '#264F78',
        'editor.inactiveSelectionBackground': '#1F2937'
    }
});

monaco.languages.registerHoverProvider('sql-demo', {
    provideHover(model, position) {
        const word = model.getWordAtPosition(position);
        if (!word) {
            return null;
        }

        const key = word.word.toUpperCase();
        const original = word.word;
        const content = hoverDocs[key] ?? hoverDocs[original];
        if (!content) {
            return null;
        }

        return {
            range: new monaco.Range(position.lineNumber, word.startColumn, position.lineNumber, word.endColumn),
            contents: [{ value: content }]
        };
    }
});

monaco.languages.registerCompletionItemProvider('sql-demo', {
    triggerCharacters: [' ', '.'],
    provideCompletionItems(model, position) {
        const word = model.getWordUntilPosition(position);
        const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: word.startColumn,
            endColumn: word.endColumn
        };

        const keywordSuggestions = sqlKeywords.map((keyword) => ({
            label: keyword,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: keyword,
            range
        }));

        const functionSuggestions = sqlFunctions.map((name) => ({
            label: name,
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: `${name}($1)`,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range
        }));

        const tableSuggestions = sqlTables.map((table) => ({
            label: table,
            kind: monaco.languages.CompletionItemKind.Class,
            insertText: table,
            detail: 'Example table',
            range
        }));

        const columnSuggestions = sqlColumns.map((column) => ({
            label: column,
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: column,
            detail: 'Example column',
            range
        }));

        const snippetSuggestions = [
            {
                label: 'SELECT statement',
                kind: monaco.languages.CompletionItemKind.Snippet,
                insertText:
                    'SELECT ${1:id}, ${2:name}\nFROM ${3:users}\nWHERE ${4:status} = ${5:\'active\'}\nORDER BY ${6:created_at} DESC\nLIMIT ${7:10};',
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: 'Basic SQL query template',
                range
            },
            {
                label: 'JOIN query',
                kind: monaco.languages.CompletionItemKind.Snippet,
                insertText:
                    'SELECT ${1:users.name}, ${2:orders.total_amount}\nFROM users\nJOIN orders ON users.id = orders.user_id\nWHERE ${3:orders.total_amount} > ${4:100};',
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: 'Join users and orders',
                range
            }
        ];

        return {
            suggestions: [
                ...snippetSuggestions,
                ...keywordSuggestions,
                ...functionSuggestions,
                ...tableSuggestions,
                ...columnSuggestions
            ]
        };
    }
});

const editor = monaco.editor.create(document.getElementById('editor')!, {
    value: `-- SQL editor demo
-- Hover SELECT, FROM, WHERE, JOIN, COUNT, or a table name
-- Press Ctrl+Space for autocomplete

SELECT
    users.id,
    users.name,
    orders.total_amount,
    COUNT(orders.id) AS order_count
FROM users
JOIN orders ON users.id = orders.user_id
WHERE orders.total_amount > 100
ORDER BY orders.created_at DESC
LIMIT 25;
`,
    language: 'sql-demo',
    theme: 'sql-demo-theme',
    automaticLayout: true,
    minimap: { enabled: false },
    lineNumbers: 'on',
    fontSize: 14,
    padding: { top: 16, bottom: 16 },
    smoothScrolling: true,
    suggestOnTriggerCharacters: true,
    quickSuggestions: {
        other: true,
        comments: false,
        strings: false
    },
    suggest: {
        showKeywords: true,
        showFunctions: true,
        showFields: true,
        showSnippets: true,
        snippetsPreventQuickSuggestions: false
    },
    hover: {
        enabled: true,
        delay: 250
    }
});

editor.focus();

console.log('Monaco SQL demo is ready!');
