import { ValidationAcceptor, ValidationChecks, ValidationRegistry } from 'langium';
import { LightlyQueryServices } from './lightly-query-module.js';
import type {
    LightlyQueryAstType,
    Query,
    Expression,
    FieldAccess,
    PropertyAccess,
    Value,
    NumberValue,
    StringValue
} from './generated/ast.js';

/**
 * Registry for validation checks.
 */
export class LightlyQueryValidationRegistry extends ValidationRegistry {
    constructor(services: LightlyQueryServices) {
        super(services);
        const validator = services.validation.LightlyQueryValidator;
        const checks: ValidationChecks<LightlyQueryAstType> = {
            Query: validator.checkQuery,
            FieldAccess: validator.checkFieldAccess,
            NumberValue: validator.checkNumberValue,
            StringValue: validator.checkStringValue
        };
        this.register(checks, validator);
    }
}

/**
 * Implementation of custom validations for the Lightly query language.
 */
export class LightlyQueryValidator {

    checkQuery(query: Query, accept: ValidationAcceptor): void {
        // Validate that the query has a valid expression
        if (!query.expression) {
            accept('warning', 'Query should have an expression', { node: query });
        }
    }

    checkFieldAccess(fieldAccess: FieldAccess, accept: ValidationAcceptor): void {
        // Validate field access patterns
        const field = fieldAccess.field;
        if (!field) {
            accept('error', 'Field access must have a field path', { node: fieldAccess });
            return;
        }

        // Check if using 'is not' or 'not in' operators
        if (fieldAccess.operator === 'is' && fieldAccess.negated) {
            // This is valid: field is not value
        } else if (fieldAccess.operator === 'in' && fieldAccess.negated) {
            // This is valid: field not in value
        } else if (fieldAccess.negated) {
            accept('warning', `The 'not' keyword is only valid with 'is' or 'in' operators`,
                { node: fieldAccess, property: 'negated' });
        }

        // Validate specific field combinations
        const baseFieldType = field.base?.type;
        const properties = field.properties || [];

        if (baseFieldType === 'ImageSampleField') {
            this.validateImageSampleFieldProperties(properties, accept, fieldAccess);
        } else if (baseFieldType === 'VideoSampleField') {
            this.validateVideoSampleFieldProperties(properties, accept, fieldAccess);
        }

        // Check for method calls with appropriate fields
        if (fieldAccess.method) {
            const methodName = fieldAccess.method.method;
            if (methodName === 'contains' || methodName === 'startswith' || methodName === 'endswith') {
                // These methods are typically for string fields
                const lastProperty = properties[properties.length - 1]?.name;
                if (lastProperty && ['width', 'height', 'size'].includes(lastProperty)) {
                    accept('warning', `Method '${methodName}' is typically used with string fields, not numeric fields`,
                        { node: fieldAccess.method });
                }
            }
        }
    }

    private validateImageSampleFieldProperties(
        properties: PropertyAccess[],
        accept: ValidationAcceptor,
        node: FieldAccess
    ): void {
        const validProperties = [
            'width', 'height', 'size', 'format', 'path', 'filename',
            'tags', 'metadata', 'predictions', 'created_at', 'updated_at',
            'dataset_id', 'sample_id', 'reviewed', 'validated', 'annotated'
        ];

        for (const prop of properties) {
            if (prop.name && !validProperties.includes(prop.name) && !/^[a-zA-Z_]\w*$/.test(prop.name)) {
                accept('warning', `Property '${prop.name}' may not be valid for ImageSampleField`,
                    { node: prop, property: 'name' });
            }
        }
    }

    private validateVideoSampleFieldProperties(
        properties: PropertyAccess[],
        accept: ValidationAcceptor,
        node: FieldAccess
    ): void {
        const validProperties = [
            'width', 'height', 'duration', 'fps', 'format', 'path', 'filename',
            'tags', 'metadata', 'predictions', 'created_at', 'updated_at',
            'dataset_id', 'sample_id', 'reviewed', 'validated', 'annotated',
            'frame_count', 'codec'
        ];

        for (const prop of properties) {
            if (prop.name && !validProperties.includes(prop.name) && !/^[a-zA-Z_]\w*$/.test(prop.name)) {
                accept('warning', `Property '${prop.name}' may not be valid for VideoSampleField`,
                    { node: prop, property: 'name' });
            }
        }
    }

    checkNumberValue(value: NumberValue, accept: ValidationAcceptor): void {
        const num = value.value;
        if (num) {
            const parsed = parseFloat(num);
            if (isNaN(parsed)) {
                accept('error', 'Invalid number format', { node: value, property: 'value' });
            }
        }
    }

    checkStringValue(value: StringValue, accept: ValidationAcceptor): void {
        const str = value.value;
        if (str) {
            // Check for unclosed quotes
            if ((str.startsWith('"') && !str.endsWith('"')) ||
                (str.startsWith("'") && !str.endsWith("'"))) {
                accept('error', 'String value has unclosed quotes', { node: value, property: 'value' });
            }
        }
    }
}