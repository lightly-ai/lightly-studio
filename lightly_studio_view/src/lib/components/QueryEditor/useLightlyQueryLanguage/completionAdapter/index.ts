/** Monaco <-> Langium/LSP completion bridge exports.
 *
 * This keeps a stable import surface for consumers while implementation
 * details live in small focused modules (one function per file).
 */
export { buildSchemaCompletions } from './completionAdapterBuildSchemaCompletions';
export { lspToMonacoCompletion } from './completionAdapterLspToMonacoCompletion';
export { syncLangiumDocument } from './completionAdapterSyncLangiumDocument';
