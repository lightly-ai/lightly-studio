// Langium dependency-injection module for the LightlyQuery language.
// The `.langium` grammar generates the parser and AST, but anything semantic
// (validation, scoping, custom completions, formatting) has to be injected
// through a services module like this one. It's the extension point for
// everything the declarative grammar can't express.
//
// Docs:
//   Services & DI:   https://langium.org/docs/reference/configuration-services/
//   Validation:      https://langium.org/docs/learn/workflow/create_validations/

import {
    EmptyFileSystem,
    createDefaultCoreModule,
    createDefaultSharedCoreModule,
    inject,
    type LangiumCoreServices,
    type LangiumSharedCoreServices
} from 'langium';
import {
    LightlyQueryGeneratedModule,
    LightlyQueryGeneratedSharedModule
} from './generated/module.js';

export type LightlyQueryServices = LangiumCoreServices;

export interface LightlyQueryServicesBundle {
    shared: LangiumSharedCoreServices;
    LightlyQuery: LightlyQueryServices;
}

// Composes three modules (later overrides earlier): Langium defaults →
// generated (grammar) → custom above. Registers the language in the shared
// ServiceRegistry so document URIs route to it.
export function createLightlyQueryServices(): LightlyQueryServicesBundle {
    const shared = inject(
        createDefaultSharedCoreModule(EmptyFileSystem),
        LightlyQueryGeneratedSharedModule
    );
    const LightlyQuery = inject(createDefaultCoreModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(LightlyQuery);
    return { shared, LightlyQuery };
}
