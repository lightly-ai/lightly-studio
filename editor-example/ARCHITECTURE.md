# How Monaco + Langium LSP Works Together

A complete walkthrough of the architecture and data flow for the Dataset Query Language editor.

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [LSP Features Deep Dive](#lsp-features-deep-dive)
5. [User Interaction Flow](#user-interaction-flow)

---

## System Overview

This project combines **Monaco Editor** (VSCode's editor) with a **custom Language Server Protocol (LSP)** built using **Langium**, all running in the browser with the LSP in a Web Worker.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (Main Thread)                    │
│                                                                   │
│  ┌──────────────────┐         ┌─────────────────────────────┐  │
│  │  Monaco Editor   │◄────────┤  MonacoLanguageClient       │  │
│  │  (UI/Rendering)  │         │  (LSP Client)                │  │
│  └──────────────────┘         └─────────────┬───────────────┘  │
│                                              │                   │
│                                              │ MessageReader/    │
│                                              │ MessageWriter     │
└──────────────────────────────────────────────┼───────────────────┘
                                               │
                                               │ postMessage
                                               │
┌──────────────────────────────────────────────▼───────────────────┐
│                    Web Worker (Background Thread)                 │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Langium Language Server                        │ │
│  │                                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │ │
│  │  │   Parser     │  │  Validator   │  │ Hover Provider  │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘ │ │
│  │                                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │ │
│  │  │ AST Builder  │  │ Scope Provider│ │Completion Provider││ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. **Grammar Definition** (`hello-lang.langium`)

This file defines the **syntax rules** for the Dataset Query Language using Langium's grammar syntax.

**What it does:**
- Defines what valid Python dataset.query() syntax looks like
- Specifies the structure: `dataset.query().match(...).order_by(...)`
- Defines logical operators: `AND()`, `OR()`, `NOT()`
- Defines query types: `ObjectDetectionQuery`, `ImageSampleField`, etc.

**Example from the grammar:**
```langium
DatasetQueryExpression:
    'dataset' '.' 'query' '(' ')' '.' 'match' '(' expression=Expression ')' 
    ('.' 'order_by' '(' orderBy=OrderByExpression ')')?;
```

This says: "A dataset query starts with 'dataset.query().match(', then an expression, then optionally '.order_by(...)'"

### 2. **Code Generation** (Langium CLI)

**Command:** `npm run langium:generate`

**Input:** `hello-lang.langium` (grammar file)

**Output:** Three generated TypeScript files in `src/language/generated/`:

1. **`ast.ts`** - TypeScript types representing the syntax tree
   ```typescript
   export interface DatasetQueryExpression {
       $type: 'DatasetQueryExpression';
       expression: Expression;
       orderBy?: OrderByExpression;
   }
   ```

2. **`grammar.ts`** - Parser configuration and rules

3. **`module.ts`** - Langium service module that wires everything together

**Why this matters:** You write the grammar once, and Langium automatically generates a type-safe parser!

### 3. **Custom Services** (Your Code)

These extend Langium's default functionality with custom logic:

#### **Validator** (`hello-lang-validator.ts`)
```typescript
export class HelloLangValidator {
    checkComparisonOperator(comparison: Comparison, accept: ValidationAcceptor) {
        if (comparison.operator === '=' && comparison.right.$type === 'STRING') {
            accept('hint', 'Use "==" for equality comparison');
        }
    }
}
```
- Runs after parsing
- Checks semantic rules
- Reports errors, warnings, and hints

#### **Hover Provider** (`dataset-query-hover.ts`)
```typescript
export class DatasetQueryHoverProvider extends AstNodeHoverProvider {
    protected getAstNodeHoverContent(node: AstNode): Hover | undefined {
        if (node.$type === 'DatasetQueryExpression') {
            return this.createHover('Dataset Query', 'Documentation here...');
        }
    }
}
```
- Triggered when user hovers over code
- Receives the AST node under cursor
- Returns markdown documentation

#### **Completion Provider** (`dataset-query-completion.ts`)
```typescript
export class DatasetQueryCompletionProvider extends DefaultCompletionProvider {
    protected override completionFor(context, next, acceptor) {
        if (textBeforeCursor.endsWith('dataset.')) {
            acceptor({
                label: 'query',
                kind: CompletionItemKind.Method,
                insertText: 'query().match($0)'
            });
        }
    }
}
```
- Triggered when user types or presses Ctrl+Space
- Analyzes text before cursor
- Provides context-aware suggestions

### 4. **Service Module** (`hello-lang-module.ts`)

This is the **dependency injection container** that wires everything together:

```typescript
export const HelloLangModule = {
    validation: {
        ValidationRegistry: (services) => new HelloLangValidationRegistry(services),
        HelloLangValidator: () => new HelloLangValidator()
    },
    lsp: {
        HoverProvider: (services) => new DatasetQueryHoverProvider(services),
        CompletionProvider: (services) => new DatasetQueryCompletionProvider(services)
    }
};
```

**What happens here:**
1. Langium's default services are created
2. Your custom services are injected
3. All services are registered and connected

### 5. **Language Server Worker** (`language-server-worker.ts`)

Runs the LSP in a **Web Worker** (background thread):

```typescript
// Create browser-compatible LSP connection
const messageReader = new BrowserMessageReader(self);
const messageWriter = new BrowserMessageWriter(self);
const connection = createConnection(messageReader, messageWriter);

// Create Langium services
const { shared } = createHelloLangServices({ connection, ...EmptyFileSystem });

// Start the language server
startLanguageServer(shared);
```

**Why Web Worker?**
- Keeps the UI responsive (parsing happens in background)
- Uses separate CPU core if available
- Doesn't block user typing or scrolling

### 6. **Monaco Editor Setup** (`main.ts`)

Connects Monaco to the LSP:

```typescript
// Register the language
monaco.languages.register({
    id: 'dataset-query',
    extensions: ['.py']
});

// Create the editor
const editor = monaco.editor.create(element, {
    language: 'dataset-query',
    suggestOnTriggerCharacters: true,  // Enable autocomplete
    hover: { enabled: true }            // Enable hover
});

// Create language client
const worker = new Worker(new URL('./language-server-worker.ts', ...));
const client = new MonacoLanguageClient({
    name: 'DatasetQuery Language Client',
    clientOptions: {
        documentSelector: [{ language: 'dataset-query' }]
    },
    connectionProvider: {
        get: () => Promise.resolve({ reader, writer })
    }
});

client.start();
```

---

## Data Flow

### Scenario 1: User Types Code

```
1. User types in Monaco Editor
   └──> Monaco updates its internal text buffer

2. Monaco sends didChange notification to language client
   └──> MonacoLanguageClient packages the change

3. Message sent to Web Worker via postMessage
   └──> BrowserMessageWriter serializes the LSP message

4. Web Worker receives message
   └──> BrowserMessageReader deserializes

5. Langium Language Server processes change
   ├──> Parser parses text into AST
   ├──> Validator runs validation rules
   └──> Diagnostics (errors/warnings) are collected

6. Diagnostics sent back to main thread
   └──> BrowserMessageWriter sends LSP response

7. Monaco receives diagnostics
   └──> MonacoLanguageClient updates editor
   └──> Red/yellow squiggles appear in editor
```

### Scenario 2: User Hovers Over Code

```
1. User hovers mouse over "dataset"
   └──> Monaco detects hover at position (line: 5, char: 10)

2. Monaco sends textDocument/hover request
   └──> Includes document URI and cursor position

3. Request sent to Web Worker
   └──> Via postMessage

4. Langium Language Server receives hover request
   ├──> Finds AST node at cursor position
   ├──> Calls DatasetQueryHoverProvider.getAstNodeHoverContent()
   ├──> Returns markdown documentation
   └──> Packages as LSP Hover response

5. Response sent back to main thread

6. Monaco displays hover tooltip
   └──> Renders markdown as formatted HTML
```

### Scenario 3: User Triggers Autocomplete

```
1. User types "dataset."
   └──> Monaco detects trigger character "."

2. Monaco sends textDocument/completion request
   └──> Includes document, position, and trigger character

3. Request sent to Web Worker

4. Langium LSP receives completion request
   ├──> DatasetQueryCompletionProvider.completionFor() is called
   ├──> Analyzes text before cursor: "dataset."
   ├──> Matches pattern and returns suggestions:
   │    [{
   │      label: 'query',
   │      kind: Method,
   │      insertText: 'query().match($0)'  // $0 = cursor position after
   │    }]
   └──> Packages as LSP CompletionList response

5. Response sent back to main thread

6. Monaco displays autocomplete menu
   └──> Shows "query" with Method icon
   └──> User presses Tab
   └──> Inserts "query().match()" with cursor inside match()
```

---

## LSP Features Deep Dive

### How Hover Works

**File:** `dataset-query-hover.ts`

**Flow:**
```typescript
// 1. User hovers at position
// 2. LSP finds AST node at that position
const node = findNodeAtPosition(document, position);

// 3. Check node type
if (node.$type === 'QueryFunction') {
    const queryFunc = node as QueryFunction;
    
    // 4. Return documentation based on node properties
    if (queryFunc.type === 'ObjectDetectionQuery' && queryFunc.method === 'match') {
        return {
            contents: {
                kind: 'markdown',
                value: '**ObjectDetectionQuery.match**\n\nFilter images...'
            }
        };
    }
}
```

**Key points:**
- Uses the **AST** (Abstract Syntax Tree) to understand code structure
- Matches on `node.$type` to determine what's being hovered
- Returns rich **Markdown** documentation
- Can include code examples, links, and formatting

### How Autocomplete Works

**File:** `dataset-query-completion.ts`

**Flow:**
```typescript
// 1. Get text before cursor
const text = context.textDocument.getText();
const textBeforeCursor = text.substring(0, context.offset);

// 2. Pattern match
if (textBeforeCursor.endsWith('dataset.')) {
    
    // 3. Add completion items
    acceptor({
        label: 'query',                    // What user sees
        kind: CompletionItemKind.Method,   // Icon type
        detail: 'Create a new query',      // Subtitle
        documentation: 'Start building...', // Help text
        insertText: 'query().match($0)',   // What gets inserted
        insertTextFormat: 2                 // 2 = snippet format
    });
}
```

**Snippet format:**
- `$0` - Final cursor position
- `${1:placeholder}` - Tab stop 1 with placeholder text
- `${2:value}` - Tab stop 2

**Example:**
```typescript
insertText: 'match(ObjectDetectionField.label == "${1:cat}")'
```
When inserted:
1. Text appears: `match(ObjectDetectionField.label == "cat")`
2. "cat" is selected (tab stop 1)
3. User can type to replace it
4. Press Tab to move to next stop

### How Validation Works

**File:** `hello-lang-validator.ts`

**Flow:**
```typescript
// 1. Parser creates AST
const ast = parser.parse(text);

// 2. Validator visits each node
for (each node in ast) {
    
    // 3. Check rules
    if (node.$type === 'Comparison') {
        if (node.operator === '=' && node.right.$type === 'STRING') {
            
            // 4. Report diagnostic
            accept('hint', 'Use "==" for equality', {
                node: node,
                property: 'operator'
            });
        }
    }
}

// 5. Diagnostics sent to editor
// Yellow squiggle appears under "="
```

---

## User Interaction Flow

### Complete Example: Typing a Query

**User types:** `dataset.query().match(ObjectDetectionField.label == "cat")`

**What happens at each step:**

#### Step 1: Type "d"
- Monaco updates buffer
- LSP re-parses (invalid syntax)
- No diagnostics yet (typing in progress)

#### Step 2: Type "dataset"
- LSP parses: recognizes "dataset" keyword
- Still invalid (incomplete)
- No errors shown yet

#### Step 3: Type "."
- **Trigger character!**
- Monaco sends completion request
- LSP checks: text ends with "dataset."
- Returns completion: `query()`
- **Autocomplete menu appears**

#### Step 4: Press Tab
- Monaco inserts: `query().match()`
- Cursor positioned inside `match()`
- LSP parses: valid so far

#### Step 5: Type "Obj"
- Monaco sends completion request
- LSP sees partial "Obj"
- Could return filtered suggestions starting with "Obj"

#### Step 6: Type "ObjectDetectionField."
- **Trigger character!**
- LSP checks: ends with "ObjectDetectionField."
- Returns completions: `label`, `confidence`, etc.
- **Autocomplete menu appears**

#### Step 7: Select "label" from menu
- Monaco inserts: `label == "placeholder"`
- Cursor in the quotes

#### Step 8: Type "cat"
- Replace placeholder with "cat"
- Complete query typed!

#### Step 9: Hover over "ObjectDetectionField"
- Monaco sends hover request at that position
- LSP finds AST node: `FieldAccess` with type="ObjectDetectionField"
- Returns hover documentation
- **Tooltip appears with markdown docs**

#### Step 10: Final validation
- LSP parses complete query
- Validator checks all rules
- All good! ✓
- No errors, warnings, or hints

---

## Message Protocol

LSP uses JSON-RPC over message passing:

### Example: Completion Request
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "method": "textDocument/completion",
  "params": {
    "textDocument": {
      "uri": "file:///path/to/file.py"
    },
    "position": {
      "line": 5,
      "character": 10
    },
    "context": {
      "triggerKind": 2,
      "triggerCharacter": "."
    }
  }
}
```

### Example: Completion Response
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "result": {
    "isIncomplete": false,
    "items": [
      {
        "label": "query",
        "kind": 2,
        "detail": "Create a new dataset query",
        "insertText": "query().match($0)",
        "insertTextFormat": 2
      }
    ]
  }
}
```

---

## Performance Considerations

### Why Web Worker?

**Main thread tasks:**
- Render UI (60 fps = 16ms per frame)
- Handle user input
- Update DOM

**Web worker tasks:**
- Parse code (can take 10-100ms for large files)
- Run validation
- Build AST
- Compute completions

**Benefit:** Parsing doesn't block rendering!

### Debouncing

Monaco debounces LSP requests:
- Doesn't send every keystroke immediately
- Waits 300ms of inactivity before sending
- Reduces unnecessary parsing

---

## Summary

The system works like this:

1. **You define grammar** → Langium generates parser
2. **You write custom services** → Hover, completion, validation
3. **Services run in Web Worker** → Non-blocking LSP
4. **Monaco connects via language client** → JSON-RPC messages
5. **User types** → LSP provides instant feedback

**The magic:** Langium handles all the complex LSP protocol details. You just write:
- Grammar (what's valid syntax)
- Validation (what's semantically correct)
- Hover (what to show)
- Completion (what to suggest)

Everything else (parsing, AST building, LSP protocol, message passing) is automatic!
