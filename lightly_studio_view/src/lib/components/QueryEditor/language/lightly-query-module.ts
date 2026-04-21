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

export type LightlyQueryAddedServices = {
    validation: {
        LightlyQueryValidator: LightlyQueryValidator;
    };
};

export type LightlyQueryServices = LangiumServices & LightlyQueryAddedServices;

export const LightlyQueryModule: Module<
    LightlyQueryServices,
    PartialLangiumServices & LightlyQueryAddedServices
> = {
    validation: {
        ValidationRegistry: (services) => new LightlyQueryValidationRegistry(services),
        LightlyQueryValidator: () => new LightlyQueryValidator()
    }
};

export function createLightlyQueryServices(context: DefaultSharedModuleContext): {
    shared: LangiumSharedServices;
    LightlyQuery: LightlyQueryServices;
} {
    const shared = createDefaultSharedModule(context);
    const LightlyQuery = inject(
        createDefaultModule({ shared }),
        LightlyQueryGeneratedModule,
        LightlyQueryModule
    );
    shared.ServiceRegistry.register(LightlyQuery);

    return { shared, LightlyQuery };
}
