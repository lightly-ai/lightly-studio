import { DefaultCompletionProvider } from 'langium/lsp';
import type { CompletionOptions } from 'vscode-languageserver';

export class LightlyQueryCompletionProvider extends DefaultCompletionProvider {
    override readonly completionOptions: CompletionOptions = {
        triggerCharacters: ['.', '(']
    };
}
