import type { ValidationAcceptor, ValidationChecks } from 'langium';
import type { HelloLangAstType, Comparison, QueryFunction } from './generated/ast.js';
import type { HelloLangServices } from './hello-lang-module.js';
import { ValidationRegistry } from 'langium';

/**
 * Register custom validation checks.
 */
export class HelloLangValidationRegistry extends ValidationRegistry {
    constructor(services: HelloLangServices) {
        super(services);
        const validator = services.validation.HelloLangValidator;
        const checks: ValidationChecks<HelloLangAstType> = {
            Comparison: validator.checkComparisonOperator,
            QueryFunction: validator.checkQueryFunction
        };
        this.register(checks, validator);
    }
}

/**
 * Implementation of custom validations.
 */
export class HelloLangValidator {

    /**
     * Validate comparison operators match field types.
     */
    checkComparisonOperator(comparison: Comparison, accept: ValidationAcceptor): void {
        // Suggest using == for string comparisons instead of =
        if (comparison.operator === '=' && comparison.right.$type === 'STRING') {
            accept('hint', 'Use "==" for equality comparison in Python syntax', {
                node: comparison,
                property: 'operator'
            });
        }
    }

    /**
     * Validate query function usage.
     */
    checkQueryFunction(query: QueryFunction, accept: ValidationAcceptor): void {
        // Check if count queries have comparison operators
        if (query.method === 'count' && !query.operator) {
            accept('warning', 'Count queries should include a comparison (e.g., == 1, >= 2)', {
                node: query,
                property: 'method'
            });
        }
    }
}
