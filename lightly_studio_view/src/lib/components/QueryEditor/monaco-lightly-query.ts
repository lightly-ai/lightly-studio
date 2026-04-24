// Monaco-side adapter for the custom LightlyQuery language. Registers the
// language, its Monarch tokenizer, editor theme, and worker factories so the
// Svelte component can stay focused on editor lifecycle.

import * as monaco from 'monaco-editor';

const LIGHTLY_QUERY_LANGUAGE_ID = 'lightly-query';
const LIGHTLY_QUERY_THEME_ID = 'lightly-query-theme';

// Monaco's language registration is global state — guard so multiple editor
// instances mounting in the same page don't re-register the language.
let isRegistered = false;

export const LIGHTLY_QUERY_DEFAULT_VALUE = `
Image.width > 600
`;

// Monaco's built-in editor worker (diffing, link detection, tokenization
// fallbacks). The LightlyQuery LSP worker is spawned directly by
// `useLightlyQueryEditor` and bridged through `MonacoLanguageClient` — it does
// not go through `MonacoEnvironment`, so this hook only serves Monaco's own
// internal worker requests.
function createEditorWorker(): Worker {
    return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url), {
        type: 'module'
    });
}

// One-shot setup: registers the language, its config, tokenizer, and theme
// with Monaco. Must run before any editor instance is created with this
// language; safe to call multiple times thanks to `isRegistered`.
export function registerLightlyQueryMonacoLanguage(): void {
    if (isRegistered) {
        return;
    }

    globalThis.MonacoEnvironment = {
        getWorker: (): Worker => createEditorWorker()
    };

    // Associate the language ID with file extensions and MIME types so Monaco
    // can auto-detect it when a model is created from a URI.
    monaco.languages.register({
        id: LIGHTLY_QUERY_LANGUAGE_ID
    });

    // Client-side Monarch tokenizer. Gives immediate syntax highlighting
    // without waiting for the LSP worker to start — the Langium server handles
    // semantics (validation, completion), but coloring is cheap enough to do
    // locally and keeps the editor responsive on first paint.
    // TODO(kondrat 04/26): Update tokenizer when language is fixed
    monaco.languages.setMonarchTokensProvider(LIGHTLY_QUERY_LANGUAGE_ID, {
        ignoreCase: true,
        tokenizer: {
            root: [
                [/#[^\n\r]*/, 'comment'],
                [/"([^"\\]|\\.)*$/, 'string.invalid'],
                [/'([^'\\]|\\.)*$/, 'string.invalid'],
                [/"/, 'string', '@doubleQuotedString'],
                [/'/, 'string', '@singleQuotedString'],
                [/tags\.contains\(/, 'predefined'],
                [/video:/, 'keyword'],
                [/\b(?:and|or|not|in)\b/, 'keyword'],
                [/\b(?:true|false)\b/, 'constant.language'],
                [
                    /\b(?:Image|ImageSampleField|Video|VideoSampleField|ObjectDetection|ObjectDetectionField)\b/,
                    'type.identifier'
                ],
                [/\b(?:object_detection|tags)\b/, 'predefined'],
                [
                    /\b(?:created_at|duration_s|file_name|file_path_abs|fps|height|label|width|x|y)\b/,
                    'identifier'
                ],
                [/[0-9]+(?:\.[0-9]*)?/, 'number'],
                [/[a-zA-Z_]\w*/, 'identifier'],
                [/==|!=|<=|>=|<|>/, 'operator'],
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

    // Custom dark theme mapping the Monarch token classes above to colors.
    // Applied by the Svelte component via the `theme` editor option.
    monaco.editor.defineTheme(LIGHTLY_QUERY_THEME_ID, {
        base: 'vs-dark',
        inherit: true,
        rules: [],
        colors: {}
    });

    isRegistered = true;
}

export { LIGHTLY_QUERY_LANGUAGE_ID, LIGHTLY_QUERY_THEME_ID };
