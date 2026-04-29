/** Hook to attach a Monaco editor instance to a DOM element */

import * as monaco from 'monaco-editor';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import lightlyQueryMonarch from './language/monarch.generated';
import { useLightlyQueryLanguage } from './useLanguageService';
import type { QueryExprTranslationResult } from './language/query-expr-translation';

const LIGHTLY_QUERY_LANGUAGE_ID = 'lightly-query';
const LIGHTLY_QUERY_THEME_ID = 'lightly-query-theme';
const LIGHTLY_QUERY_DEFAULT_VALUE = `Image.width > 1920 AND tags.contains("reviewed")
AND object_detection(label == "car" and x > 10)
`;

self.MonacoEnvironment = {
    getWorker() {
        return new editorWorker();
    }
};

export type TranslateQueryReturn = QueryExprTranslationResult;

/**
 * Setup Monaco editor with the lightly query language and theme.
 */
const setupMonaco = () => {
    monaco.languages.register({
        id: LIGHTLY_QUERY_LANGUAGE_ID
    });
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
};

/**
 * Hook to create and manage a Monaco editor instance for editing lightly query expressions.
 */
export const useQueryEditor = () => {
    const language = useLightlyQueryLanguage();

    const mount = (el: HTMLElement) => {
        const value = LIGHTLY_QUERY_DEFAULT_VALUE;
        const uri = monaco.Uri.parse(`inmemory://model/lightly-query.lql`);
        const model = monaco.editor.createModel(value, LIGHTLY_QUERY_LANGUAGE_ID, uri);

        setupMonaco();

        monaco.editor.create(el, {
            model,
            theme: LIGHTLY_QUERY_THEME_ID,
            automaticLayout: true
        });

        language.attach(model);
    };

    return { mount, translateQuery: language.translateQuery };
};
