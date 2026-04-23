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
import { QueryExprNotification, toQueryExpr } from './query-expr-notification.js';

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

    // After every successful parse (or failed lex/parse), send the result to
    // the main thread as a custom LSP notification. `onDocumentPhase` fires
    // per-document even when rapid typing cancels in-flight builds, so the
    // main thread always gets the latest state.
    shared.workspace.DocumentBuilder.onDocumentPhase(DocumentState.Validated, (document) => {
        const connection = shared.lsp?.Connection;
        if (!connection) return;

        const { lexerErrors, parserErrors } = document.parseResult;
        if (lexerErrors.length > 0 || parserErrors.length > 0) {
            connection.sendNotification(QueryExprNotification, {
                status: 'error',
                errors: [...lexerErrors, ...parserErrors].map((e) => ({
                    message: e.message,
                    line: 'line' in e ? (e.line as number) : undefined,
                    column: 'column' in e ? (e.column as number) : undefined
                }))
            });
        } else {
            connection.sendNotification(QueryExprNotification, {
                status: 'ok',
                queryExpr: toQueryExpr(document.parseResult.value)
            });
        }
    });

    return shared;
}
