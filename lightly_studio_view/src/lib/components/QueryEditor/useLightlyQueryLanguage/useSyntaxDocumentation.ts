/** Module to register hover provider */
import * as monaco from 'monaco-editor';
import { getHover } from './syntaxDocumentation/getHover';

// Registers the Monaco hover provider for the LightlyQuery language. Must be
// called exactly once per language id (e.g. from one-time editor setup).
// Monaco merges results from every registered provider, so calling this more
// than once produces duplicated hover content.
export function useSyntaxDocumentation(params: { languageId: string }) {
    monaco.languages.registerHoverProvider(params.languageId, {
        provideHover: (model, position) => getHover(model, position)
    });
}
