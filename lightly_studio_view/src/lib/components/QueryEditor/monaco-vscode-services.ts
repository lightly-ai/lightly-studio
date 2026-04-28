// One-time initialization of the VSCode API services that `monaco-languageclient`.

import { LogLevel } from '@codingame/monaco-vscode-api';
import { MonacoVscodeApiWrapper } from 'monaco-languageclient/vscodeApiWrapper';

let startupPromise: Promise<void> | null = null;

export function ensureMonacoVscodeServices(): Promise<void> {
    if (!startupPromise) {
        const wrapper = new MonacoVscodeApiWrapper({
            $type: 'classic',
            viewsConfig: { $type: 'EditorService' },
            logLevel: LogLevel.Warning
        });
        // Only the first call's promise is returned.
        const attempt = wrapper.start({ caller: 'LightlyQueryEditor' }).catch((err) => {
            if (startupPromise === attempt) {
                startupPromise = null;
            }
            throw err;
        });
        startupPromise = attempt;
    }
    return startupPromise;
}
