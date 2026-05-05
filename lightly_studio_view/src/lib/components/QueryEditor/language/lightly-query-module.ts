// Langium dependency-injection module for the LightlyQuery language.
// The `.langium` grammar generates the parser and AST, but anything semantic
// (validation, scoping, custom completions, formatting) has to be injected
// through a services module like this one. It's the extension point for
// everything the declarative grammar can't express.
//
// Docs:
//   Services & DI:   https://langium.org/docs/reference/configuration-services/
//   Validation:      https://langium.org/docs/learn/workflow/create_validations/

import { EmptyFileSystem, inject } from 'langium';
import {
    createDefaultModule,
    createDefaultSharedModule,
    type LangiumServices,
    type LangiumSharedServices
} from 'langium/lsp';
import {
    LightlyQueryGeneratedModule,
    LightlyQueryGeneratedSharedModule
} from './generated/module.js';

export type LightlyQueryServices = LangiumServices;

export interface LightlyQueryServicesBundle {
    shared: LangiumSharedServices;
    LightlyQuery: LightlyQueryServices;
}

// Composes three modules (later overrides earlier): Langium defaults →
// generated (grammar) → custom above. Registers the language in the shared
// ServiceRegistry so document URIs route to it. We pull from `langium/lsp`
// to get the bundled provider classes (CompletionProvider, HoverProvider, …)
// but never start an LSP transport: the providers are invoked directly on
// the main thread.
export function createLightlyQueryServices(): LightlyQueryServicesBundle {
    const shared = inject(
        createDefaultSharedModule(EmptyFileSystem),
        LightlyQueryGeneratedSharedModule
    );
    const LightlyQuery = inject(createDefaultModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(LightlyQuery);
    return { shared, LightlyQuery };
}
