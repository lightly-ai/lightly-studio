/** Hook to attach a Monaco editor instance to a DOM element */

import * as monaco from 'monaco-editor';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import lightlyQueryMonarch from './language/monarch.generated';

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

export const useQueryEditor = () => {
    const mount = (el: HTMLElement) => {
        const value = LIGHTLY_QUERY_DEFAULT_VALUE;
        const uri = monaco.Uri.parse(`inmemory://model/lightly-query.lql`);
        const model = monaco.editor.createModel(value, LIGHTLY_QUERY_LANGUAGE_ID, uri);

        setupMonaco();

        monaco.editor.create(el!, {
            model,
            theme: LIGHTLY_QUERY_THEME_ID,
            automaticLayout: true
        });
    };

    return { mount };
};
