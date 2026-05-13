/** Hook to attach a Monaco editor instance to a DOM element */

import * as monaco from 'monaco-editor';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import lightlyQueryMonarch from './language/monarch.generated';
import { useLightlyQueryLanguage } from './useLightlyQueryLanguage/useLightlyQueryLanguage';
import { useSyntaxCompletion } from './useLightlyQueryLanguage/useSyntaxCompletion';
import { useSyntaxDocumentation } from './useLightlyQueryLanguage/useSyntaxDocumentation';

const LIGHTLY_QUERY_LANGUAGE_ID = 'lightly-query';
const LIGHTLY_QUERY_THEME_ID = 'lightly-query-theme';

/** Regex source for the STRING terminal in the generated Monarch grammar. */
const STRING_REGEX_SOURCE = `"([^"\\\\\\n\\r]|\\\\.)*"|'([^'\\\\\\n\\r]|\\\\.)*'`;

/**
 * Patch the generated Monarch config so that quoted strings use the
 * `string.quoted` token instead of the generic `string` token.
 * This lets us style them differently from field-name keywords.
 */
const patchStringToken = (
    config: monaco.languages.IMonarchLanguage
): monaco.languages.IMonarchLanguage => {
    const patched = structuredClone(config);
    const tokenizer = (patched as Record<string, unknown>).tokenizer as
        | Record<string, Array<{ regex: RegExp; action: { token: string } }>>
        | undefined;
    const rules = tokenizer?.initial;
    if (rules) {
        for (const rule of rules) {
            if (rule.regex?.source === STRING_REGEX_SOURCE) {
                rule.action = { token: 'string.quoted' };
                break;
            }
        }
    }
    return patched;
};

self.MonacoEnvironment = {
    getWorker() {
        return new editorWorker();
    }
};

interface MountOptions {
    value: string;
    readOnly?: boolean;
    onChange?: (value: string) => void;
}

let monacoSetupDone = false;

const setupMonaco = () => {
    if (monacoSetupDone) return;
    monaco.languages.register({ id: LIGHTLY_QUERY_LANGUAGE_ID });
    monaco.languages.setMonarchTokensProvider(
        LIGHTLY_QUERY_LANGUAGE_ID,
        patchStringToken(lightlyQueryMonarch as monaco.languages.IMonarchLanguage)
    );
    useSyntaxDocumentation({ languageId: LIGHTLY_QUERY_LANGUAGE_ID });
    useSyntaxCompletion({ languageId: LIGHTLY_QUERY_LANGUAGE_ID });
    monaco.editor.defineTheme(LIGHTLY_QUERY_THEME_ID, {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'string', foreground: '569cd6' },
            { token: 'string.quoted', foreground: 'ce9178' }
        ],
        colors: {}
    });
    monacoSetupDone = true;
};

let modelCounter = 0;

/**
 * Hook to create and manage a Monaco editor instance for editing lightly query expressions.
 */
export const useQueryEditor = () => {
    const language = useLightlyQueryLanguage();

    const mount = (el: HTMLElement, options: MountOptions): (() => void) => {
        setupMonaco();

        // Each mount gets a unique URI; otherwise Monaco throws
        // "Cannot add model because it already exists!" on remount.
        const uri = monaco.Uri.parse(`inmemory://model/lightly-query-${++modelCounter}.lql`);
        const model = monaco.editor.createModel(options.value, LIGHTLY_QUERY_LANGUAGE_ID, uri);

        const editor = monaco.editor.create(el, {
            model,
            theme: LIGHTLY_QUERY_THEME_ID,
            automaticLayout: true,
            readOnly: options.readOnly ?? false,
            minimap: { enabled: false },
            wordWrap: 'on',
            fixedOverflowWidgets: true,
            scrollBeyondLastLine: false
        });

        const detachLanguage = language.attach(model);
        const contentSub = model.onDidChangeContent(() => {
            options.onChange?.(model.getValue());
        });

        return () => {
            contentSub.dispose();
            detachLanguage();
            editor.dispose();
            model.dispose();
        };
    };

    return { mount, translateQuery: language.translateQuery };
};
