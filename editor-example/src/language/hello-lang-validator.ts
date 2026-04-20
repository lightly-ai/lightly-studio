import type { ValidationAcceptor, ValidationChecks } from 'langium';
import type { HelloLangAstType, Greeting, Person } from './generated/ast.js';
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
            Greeting: validator.checkGreeting,
            Person: validator.checkPersonCapitalized
        };
        this.register(checks, validator);
    }
}

/**
 * Implementation of custom validations.
 */
export class HelloLangValidator {

    /**
     * Validate that greetings use exclamation marks for enthusiasm!
     */
    checkGreeting(greeting: Greeting, accept: ValidationAcceptor): void {
        if (greeting.punctuation === '.') {
            accept('warning', 'Greetings should be enthusiastic! Use "!" instead of "."', {
                node: greeting,
                property: 'punctuation'
            });
        }
    }

    /**
     * Validate that person names start with a capital letter.
     */
    checkPersonCapitalized(person: Person, accept: ValidationAcceptor): void {
        if (person.name) {
            const firstChar = person.name.charAt(0);
            if (firstChar.toUpperCase() !== firstChar) {
                accept('warning', 'Person name should start with a capital letter.', {
                    node: person,
                    property: 'name'
                });
            }
        }
    }
}
