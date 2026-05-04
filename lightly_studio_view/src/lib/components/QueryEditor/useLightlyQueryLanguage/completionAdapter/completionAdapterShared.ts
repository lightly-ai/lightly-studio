import * as monaco from 'monaco-editor';
import { CompletionItemKind as LspCompletionItemKind } from 'vscode-languageserver-types';

export const ALLOWED_NESTED_KEYWORDS = new Set(['AND', 'OR', 'NOT']);

const MONACO_KIND = monaco.languages.CompletionItemKind;
const LSP_KIND = LspCompletionItemKind;
export const LSP_TO_MONACO_KIND: Readonly<Record<number, monaco.languages.CompletionItemKind>> = {
    [LSP_KIND.Text]: MONACO_KIND.Text,
    [LSP_KIND.Method]: MONACO_KIND.Method,
    [LSP_KIND.Function]: MONACO_KIND.Function,
    [LSP_KIND.Constructor]: MONACO_KIND.Constructor,
    [LSP_KIND.Field]: MONACO_KIND.Field,
    [LSP_KIND.Variable]: MONACO_KIND.Variable,
    [LSP_KIND.Class]: MONACO_KIND.Class,
    [LSP_KIND.Interface]: MONACO_KIND.Interface,
    [LSP_KIND.Module]: MONACO_KIND.Module,
    [LSP_KIND.Property]: MONACO_KIND.Property,
    [LSP_KIND.Unit]: MONACO_KIND.Unit,
    [LSP_KIND.Value]: MONACO_KIND.Value,
    [LSP_KIND.Enum]: MONACO_KIND.Enum,
    [LSP_KIND.Keyword]: MONACO_KIND.Keyword,
    [LSP_KIND.Snippet]: MONACO_KIND.Snippet,
    [LSP_KIND.Color]: MONACO_KIND.Color,
    [LSP_KIND.File]: MONACO_KIND.File,
    [LSP_KIND.Reference]: MONACO_KIND.Reference,
    [LSP_KIND.Folder]: MONACO_KIND.Folder,
    [LSP_KIND.EnumMember]: MONACO_KIND.EnumMember,
    [LSP_KIND.Constant]: MONACO_KIND.Constant,
    [LSP_KIND.Struct]: MONACO_KIND.Struct,
    [LSP_KIND.Event]: MONACO_KIND.Event,
    [LSP_KIND.Operator]: MONACO_KIND.Operator,
    [LSP_KIND.TypeParameter]: MONACO_KIND.TypeParameter
};
