/** Hook to attach a Monaco editor instance to a DOM element */

import * as monaco from 'monaco-editor';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import lightlyQueryMonarch from './language/monarch.generated';
import { useLightlyQueryLanguage } from './useLanguageService';
import type { QueryExprTranslationResult } from './language/query-expr-translation';

const LIGHTLY_QUERY_LANGUAGE_ID = 'lightly-query';
const LIGHTLY_QUERY_THEME_ID = 'lightly-query-theme';

self.MonacoEnvironment = {
    getWorker() {
        return new editorWorker();
    }
};

export type TranslateQueryReturn = QueryExprTranslationResult;

export interface MountOptions {
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
        lightlyQueryMonarch as monaco.languages.IMonarchLanguage
    );
    monaco.editor.defineTheme(LIGHTLY_QUERY_THEME_ID, {
        base: 'vs-dark',
        inherit: true,
        rules: [],
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
            readOnly: options.readOnly ?? false
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
