// Langium dependency-injection module for the LightlyQuery language.
// The `.langium` grammar generates the parser and AST, but anything semantic
// (validation, scoping, custom completions, formatting) has to be injected
// through a services module like this one. It's the extension point for
// everything the declarative grammar can't express.
//
// Docs:
//   Services & DI:   https://langium.org/docs/reference/configuration-services/
//   Validation:      https://langium.org/docs/learn/workflow/create_validations/

import { DocumentState, inject } from 'langium';
import {
    createDefaultModule,
    createDefaultSharedModule,
    type DefaultSharedModuleContext,
    type LangiumServices,
    type LangiumSharedServices
} from 'langium/lsp';
import {
    LightlyQueryGeneratedModule,
    LightlyQueryGeneratedSharedModule
} from './generated/module.js';
import {
    QueryExprTranslationRequest,
    type QueryExprTranslationResult,
    toQueryExpr
} from './query-expr-translation.js';
import { isQuery } from './generated/ast.js';

export type LightlyQueryServices = LangiumServices;

// Composes three modules (later overrides earlier): Langium defaults →
// generated (grammar) → custom above. Registers the language in the shared
// ServiceRegistry so document URIs route to it.
export function createLightlyQueryServices(
    context: DefaultSharedModuleContext
): LangiumSharedServices {
    const shared = inject(createDefaultSharedModule(context), LightlyQueryGeneratedSharedModule);
    const LightlyQuery = inject(createDefaultModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(LightlyQuery);
    let latestTranslation: QueryExprTranslationResult | null = null;

    shared.lsp?.Connection?.onRequest(QueryExprTranslationRequest, () => latestTranslation);

    // `onDocumentPhase` fires per-document even when rapid typing cancels
    // in-flight builds, so the worker-side cache stays aligned with the most
    // recent validation result for the active buffer.
    shared.workspace.DocumentBuilder.onDocumentPhase(DocumentState.Validated, (document) => {
        if (!isQuery(document.parseResult.value)) {
            latestTranslation = null;
            return;
        }
        latestTranslation = toQueryExpr({
            lexerErrors: document.parseResult.lexerErrors,
            parserErrors: document.parseResult.parserErrors,
            value: document.parseResult.value
        });
    });

    return shared;
}
