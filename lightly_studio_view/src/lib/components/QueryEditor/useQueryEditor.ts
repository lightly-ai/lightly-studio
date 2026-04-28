/** Hook to attach a Monaco editor instance to a DOM element */
// import * as monaco from '@codingame/monaco-vscode-editor-api';
// import { MonacoVscodeApiWrapper } from 'monaco-languageclient/vscodeApiWrapper';
// import { LogLevel } from '@codingame/monaco-vscode-api';

import * as monaco from 'monaco-editor';

self.MonacoEnvironment = {
    getWorker: function () {
        return new Worker(
            new URL('monaco-editor/esm/vs/editor/editor.worker.js', import.meta.url),
            {
                type: 'module'
            }
        );
    }
};

export const useQueryEditor = () => {
    const mount = (el: HTMLElement) => {
        monaco.editor.create(el!);
    };

    return { mount };
};
