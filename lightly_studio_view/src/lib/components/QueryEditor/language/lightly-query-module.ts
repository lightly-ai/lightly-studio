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
    createDefaultModule,
    createDefaultSharedModule,
    type DefaultSharedModuleContext,
    inject,
    type LangiumServices,
    type LangiumSharedServices,
    type PartialLangiumServices
} from 'langium';
import { LightlyQueryGeneratedModule } from './generated/module.js';
import {
    LightlyQueryValidationRegistry,
    LightlyQueryValidator
} from './lightly-query-validator.js';

// Services this language adds on top of Langium's defaults.
export type LightlyQueryAddedServices = {
    validation: {
        LightlyQueryValidator: LightlyQueryValidator;
    };
};

export type LightlyQueryServices = LangiumServices & LightlyQueryAddedServices;

// DI module — keys here override the default and generated modules.
//
// Example: add "type '.' → suggest fields" by subclassing
// DefaultCompletionProvider and registering under `lsp.CompletionProvider`:
//
//   class LightlyQueryCompletionProvider extends DefaultCompletionProvider {
//       override readonly completionOptions = { triggerCharacters: ['.'] };
//       protected override completionFor(ctx, next, accept) { /* emit items */ }
//   }
//   // lsp: { CompletionProvider: (s) => new LightlyQueryCompletionProvider(s) }
export const LightlyQueryModule: Module<
    LightlyQueryServices,
    PartialLangiumServices & LightlyQueryAddedServices
> = {
    validation: {
        ValidationRegistry: (services) => new LightlyQueryValidationRegistry(services),
        LightlyQueryValidator: () => new LightlyQueryValidator()
    }
};

// Composes three modules (later overrides earlier): Langium defaults →
// generated (grammar) → custom above. Registers the language in the shared
// ServiceRegistry so document URIs route to it.
export function createLightlyQueryServices(
    context: DefaultSharedModuleContext
): LangiumSharedServices {
    const shared = createDefaultSharedModule(context);
    const LightlyQuery = inject(
        createDefaultModule({ shared }),
        LightlyQueryGeneratedModule,
        LightlyQueryModule
    );
    shared.ServiceRegistry.register(LightlyQuery);
    return shared;
}
