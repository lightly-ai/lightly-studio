# Best Practices

## Design Principles

Apply SOLID principles to create maintainable, scalable components.

### Single responsibility

Function or module should have one reason to change. If it has two, split it.
Do not mix data fetching, business logic and presentation in the same component.
Small files are welcome.

### Minimal interfaces

Components should only accept the data that they actually use. Avoid passing entire objects
when a few fields suffice. Create an abstracted interface that only exposes what the component
needs.

### Composition over inheritance

Don't create deep class hierarchies. Build complex behavior by combining small, focused units.
Use dependency injection and inversion.

## Managing Complexity

### Split Large Units

When adding new code, always consider splitting the logic into a new function, component or a file.
As a rule of thumb:

- Functions should be under 20 lines
- Files should be under 400 lines

### Reducing Complexity

Keep logic easy to understand by reducing horizontal, vertical and cyclomatic complexity.
As a rule of thumb:

- **Nesting depth** should be under 3 levels — use early returns to flatten
- **Conditional branches** per function should be limited - extract complex logic into separate functions
- **Extract helper variables** instead of writing complex inline expressions
