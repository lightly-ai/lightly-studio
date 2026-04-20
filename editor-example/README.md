# Monaco Editor +

 Langium LSP - Dataset Query Example

A complete example demonstrating **Monaco Editor** with **Langium LSP** for validating Python `dataset.query()` syntax in the browser.

## What is this?

This project showcases:
- 🎯 **Monaco Editor** - VSCode's editor running in the browser
- 🔧 **Langium** - Builds a custom LSP for Python dataset queries
- ⚡ **Web Worker** - LSP runs in background thread (non-blocking)
- 🐍 **Python Syntax** - Native `dataset.query()` API with validation

## Supported Syntax

The editor validates Python `dataset.query()` expressions:

### Basic Queries

```python
# Find images with at least one cat
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
)

# Logical AND - exactly 1 cat and 1 dog
dataset.query().match(
    AND(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat") == 1,
        ObjectDetectionQuery.count(ObjectDetectionField.label == "dog") == 1
    )
)

# Logical OR - exactly 1 cat or 1 dog
dataset.query().match(
    OR(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat") == 1,
        ObjectDetectionQuery.count(ObjectDetectionField.label == "dog") == 1
    )
)

# Negation - images without cats
dataset.query().match(
    NOT(ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"))
)
```

### Metadata Queries

```python
# Cats in large images
dataset.query().match(
    AND(
        ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
        ImageSampleField.width > 500
    )
)

# Multiple metadata conditions
dataset.query().match(
    AND(
        ImageSampleField.width > 500,
        ImageSampleField.height > 300,
        ImageSampleField.created_at > "2024-01-01"
    )
)
```

### Annotation Counting

```python
# At least 3 people
dataset.query().match(
    ObjectDetectionQuery.count(ObjectDetectionField.label == "person") >= 3
)

# At most 5 cars
dataset.query().match(
    ObjectDetectionQuery.count(ObjectDetectionField.label == "car") <= 5
)

# No bicycles
dataset.query().match(
    ObjectDetectionQuery.count(ObjectDetectionField.label == "bicycle") == 0
)
```

### Sorting

```python
# Sort by width (descending)
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
).order_by(
    OrderByField(ImageSampleField.width).desc()
)

# Sort by annotation count
dataset.query().match(
    AND(
        ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
        ImageSampleField.width > 500
    )
).order_by(
    OrderByField(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat")
    ).desc()
)

# Sort by text similarity
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
).order_by(
    OrderByField(ImageSampleField.text_similarity("outdoor scene"))
)
```

## Supported Features

| Feature | Supported | Example |
|---------|-----------|---------|
| Object detection queries | ✅ | `ObjectDetectionQuery.match(...)` |
| Annotation counting | ✅ | `ObjectDetectionQuery.count(...) >= 2` |
| Metadata filtering | ✅ | `ImageSampleField.width > 500` |
| Logical operators | ✅ | `AND(...)`, `OR(...)`, `NOT(...)` |
| Nested expressions | ✅ | `AND(OR(...), ...)` |
| Sorting | ✅ | `.order_by(OrderByField(...).desc())` |
| Text similarity | ✅ | `ImageSampleField.text_similarity("text")` |
| Comparison operators | ✅ | `==`, `!=`, `>`, `<`, `>=`, `<=` |

## Validation Features

- ✅ **Syntax validation** - Real-time Python syntax checking
- ⚠️ **Comparison operator hints** - Suggests `==` instead of `=` for equality
- 💡 **Count query warnings** - Warns if count queries lack comparisons
- 🚀 **LSP in Web Worker** - Non-blocking, runs in background thread
- 🎯 **Hover information** - Hover over keywords to see documentation
- ⚡ **Autocomplete** - Press `.` after `dataset`, field types, or query types for suggestions

## LSP Features

### Hover Documentation

Hover over any element to see documentation:
- **`dataset`** - Shows dataset query API documentation
- **`ObjectDetectionQuery.match`** - Explains match method
- **`ObjectDetectionQuery.count`** - Explains count method  
- **`ImageSampleField.width`** - Shows field documentation
- **`ObjectDetectionField.label`** - Shows annotation field docs

### Autocomplete (IntelliSense)

Press `.` (dot) after these to get autocomplete suggestions:

1. **After `dataset.`** → Suggests `query()` method
2. **After `ObjectDetectionQuery.`** → Suggests `match()` and `count()` methods
3. **After `ObjectDetectionField.`** → Suggests fields: `label`, `confidence`, `bbox_x`, etc.
4. **After `ImageSampleField.`** → Suggests fields: `width`, `height`, `created_at`, `text_similarity()`, etc.
5. **After `ClassificationField.`** → Suggests `label`, `confidence`
6. **After `OrderByField(...).`** → Suggests `desc()`, `asc()`
7. **After `)` (closing match)**  → Suggests `.order_by()`

**Trigger autocomplete manually:** Press `Ctrl+Space` (Windows/Linux) or `Cmd+Space` (Mac)

## Setup

```bash
# Install dependencies
npm install

# Generate TypeScript from Langium grammar
npm run langium:generate

# Start dev server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

**Try the LSP features:**
1. Open [try-lsp-features.py](try-lsp-features.py) in the editor
2. **Hover** over `dataset`, `ObjectDetectionQuery`, or any field to see documentation
3. **Type `.`** after `dataset`, `ObjectDetectionField`, or `ImageSampleField` to see autocomplete suggestions
4. **Press `Ctrl+Space`** (or `Cmd+Space` on Mac) anywhere to manually trigger autocomplete

See [examples.py](examples.py) for more query patterns!

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Project Structure

```
editor-example/
├── src/
│   ├── language/
│   │   ├── hello-lang.langium          # Grammar definition
│   │   ├── hello-lang-module.ts        # Langium services
│   │   ├── hello-lang-validator.ts     # Custom validation
│   │   └── generated/                  # Auto-generated from grammar
│   ├── language-server-worker.ts       # LSP worker (runs in Web Worker)
│   └── main.ts                         # Monaco editor setup
├── index.html                          # Entry point
├── examples.py                         # Example queries
├── package.json
├── tsconfig.json
├── vite.config.ts
└── langium-config.json
```

## How It Works

### 1. Grammar Definition (`hello-lang.langium`)
Defines Python `dataset.query()` syntax using Langium:
- `dataset.query().match(...)`
- `AND(...)`, `OR(...)`, `NOT(...)`
- `ObjectDetectionQuery.match/count(...)`
- `ImageSampleField.field > value`
- `.order_by(OrderByField(...).desc())`

### 2. Code Generation
Run `npm run langium:generate` to generate:
- **AST types** (`generated/ast.ts`) - TypeScript types for the syntax tree
- **Grammar structure** (`generated/grammar.ts`) - Parser configuration
- **Service module** (`generated/module.ts`) - Langium services

### 3. Language Server Worker (`language-server-worker.ts`)
Runs Langium LSP in a Web Worker:
- Creates browser-compatible LSP connection
- Initializes Langium services
- Provides validation, parsing, and (future) autocomplete

### 4. Monaco Editor (`main.ts`)
Sets up Monaco and connects to LSP:
- Registers `dataset-query` language
- Creates Monaco editor instance
- Creates `MonacoLanguageClient` for LSP communication
- Starts language client

### 5. Communication Flow
```
Monaco Editor (main thread)
    ↕ BrowserMessageReader/Writer
Web Worker (language-server-worker.ts)
    ↕ Langium LSP
Dataset Query Parser & Validator
```

## Extending the Language

### Add New Query Types

Edit `src/language/hello-lang.langium`:

```langium
QueryType:
    'ObjectDetectionQuery' |
    'ClassificationQuery' |
    'InstanceSegmentationQuery' |
    'VideoQuery';  // Add new type
```

Then run:
```bash
npm run langium:generate
```

### Add Custom Validation

Edit `src/language/hello-lang-validator.ts`:

```typescript
export class HelloLangValidator {
    checkCustomRule(node: ASTNode, accept: ValidationAcceptor): void {
        // Your validation logic
    }
}
```

Register in `HelloLangValidationRegistry`:

```typescript
const checks: ValidationChecks<HelloLangAstType> = {
    ASTNodeType: validator.checkCustomRule
};
```

### Add Custom Hover Documentation

Edit `src/language/dataset-query-hover.ts`:

```typescript
protected getAstNodeHoverContent(node: AstNode): Hover | undefined {
    if (node.$type === 'YourCustomType') {
        return this.createHover(
            'Title',
            'Your documentation here'
        );
    }
}
```

### Add Custom Autocomplete

Edit `src/language/dataset-query-completion.ts`:

```typescript
protected override completionFor(
    context: CompletionContext,
    next: NextFeature,
    acceptor: CompletionAcceptor
): void {
    const text = context.textDocument.getText();
    const textBeforeCursor = text.substring(0, context.offset);
    
    if (textBeforeCursor.endsWith('YourType.')) {
        acceptor({
            label: 'method',
            kind: CompletionItemKind.Method,
            detail: 'Method description',
            insertText: 'method(${1:arg})',
            insertTextFormat: 2  // Snippet format
        });
    }
}
```

## Technologies

- [Monaco Editor](https://microsoft.github.io/monaco-editor/) v0.50.0
- [Langium](https://langium.org/) v3.0.0
- [monaco-languageclient](https://github.com/TypeFox/monaco-languageclient) v8.6.0
- [Vite](https://vitejs.dev/) v5.3.0
- TypeScript v5.5.3

## Learn More

- [Langium Documentation](https://langium.org/docs/)
- [Monaco Editor API](https://microsoft.github.io/monaco-editor/api/index.html)
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)

## License

This example is provided for educational purposes.
