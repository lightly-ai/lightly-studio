// Semantic validation for LightlyQuery ASTs. Runs inside the Langium LSP
// worker after parsing succeeds, producing diagnostics (info/warning/error)
// that the Monaco language client surfaces as squigglies in the editor.
//
// Docs: https://langium.org/docs/learn/workflow/create_validations/

import type { ValidationAcceptor, ValidationChecks } from 'langium';
import { ValidationRegistry } from 'langium';
import type { LightlyQueryServices } from './lightly-query-module.js';
import type { LightlyQueryAstType, Query } from './generated/ast.js';

// Wires validator methods to specific AST node types. Langium dispatches a
// registered check whenever it finishes validating a node of that type; the
// `ValidationChecks<LightlyQueryAstType>` type ensures the mapping only
// references node types the grammar actually produces.
//
// See: https://langium.org/docs/learn/workflow/create_validations/#registering-validation-checks
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

// Container for the validator methods themselves. Each `checkXxx` method
// receives the AST node and a `ValidationAcceptor` used to emit diagnostics.
// Keep checks side-effect-free and fast — they run on every document change.
//
// ValidationAcceptor API: https://langium.org/docs/learn/workflow/create_validations/#implementing-validation-checks
export class LightlyQueryValidator {
    // Warns when a query has no expression body. `{ node: query }` anchors the
    // diagnostic to the whole `Query` node; pass a `property` or `range`
    // instead to highlight a specific token.
    checkQuery(query: Query, accept: ValidationAcceptor): void {
        if (!query.expression) {
            accept('warning', 'Query should have an expression.', { node: query });
        }
    }
}
