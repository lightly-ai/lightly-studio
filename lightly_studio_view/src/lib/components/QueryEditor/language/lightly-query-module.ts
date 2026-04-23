// Langium dependency-injection module for the LightlyQuery language.
// The `.langium` grammar generates the parser and AST, but anything semantic
// (validation, scoping, custom completions, formatting) has to be injected
// through a services module like this one. It's the extension point for
// everything the declarative grammar can't express.
//
// Docs:
//   Services & DI:   https://langium.org/docs/reference/configuration-services/
//   Validation:      https://langium.org/docs/learn/workflow/create_validations/

import type { Module } from 'langium';
import {
    createDefaultCoreModule,
    createDefaultModule,
    createDefaultSharedCoreModule,
    createDefaultSharedModule,
    type DefaultSharedModuleContext,
    EmptyFileSystem,
    inject,
    type LangiumCoreServices,
    type LangiumServices,
    type LangiumSharedServices
} from 'langium';
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
    const shared = createDefaultSharedModule(context);
    const LightlyQuery = inject(createDefaultModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(LightlyQuery);
    return shared;
}

// Lightweight core-only services (no LSP wiring) — suitable for main-thread
// parsing where a full language server is not needed.
export function createLightlyQueryCoreServices(): LangiumCoreServices {
    const shared = inject(
        createDefaultSharedCoreModule(EmptyFileSystem),
        LightlyQueryGeneratedSharedModule
    );
    const services = inject(createDefaultCoreModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(services);
    return services;
}
