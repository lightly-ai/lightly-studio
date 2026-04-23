// Langium dependency-injection module for the LightlyQuery language.
// The `.langium` grammar generates the parser and AST, but anything semantic
// (validation, scoping, custom completions, formatting) has to be injected
// through a services module like this one. It's the extension point for
// everything the declarative grammar can't express.
//
// Docs:
//   Services & DI:   https://langium.org/docs/reference/configuration-services/
//   Validation:      https://langium.org/docs/learn/workflow/create_validations/

import { inject } from 'langium';
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
    return shared;
}
