import type { ValidationAcceptor, ValidationChecks } from 'langium';
import { ValidationRegistry } from 'langium';
import type { LightlyQueryServices } from './lightly-query-module.js';
import type { LightlyQueryAstType, Query } from './generated/ast.js';

export class LightlyQueryValidationRegistry extends ValidationRegistry {
    constructor(services: LightlyQueryServices) {
        super(services);
        const validator = services.validation.LightlyQueryValidator;
        const checks: ValidationChecks<LightlyQueryAstType> = {
            Query: validator.checkQuery
        };
        this.register(checks, validator);
    }
}

export class LightlyQueryValidator {
    checkQuery(query: Query, accept: ValidationAcceptor): void {
        if (!query.expression) {
            accept('warning', 'Query should have an expression.', { node: query });
        }
    }
}
