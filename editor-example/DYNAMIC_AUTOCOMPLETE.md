# Dynamic Autocomplete with API Integration

This guide explains how to extend the tag autocomplete feature to fetch suggestions from your backend API.

## Current Implementation

The editor currently uses **hardcoded tags** for autocomplete:

```typescript
const availableTags = [
    'reviewed',
    'needs-labeling',
    'approved',
    // ... more tags
];
```

When you type `ImageSampleField.tags.contains("`, Monaco shows these suggestions.

## API Integration Pattern

### 1. Basic Async Fetch

Replace the hardcoded array with an API call:

```typescript
// Cache for tags
let cachedTags: string[] = [];
let tagsPromise: Promise<string[]> | null = null;

async function fetchAvailableTags(): Promise<string[]> {
    if (tagsPromise) {
        return tagsPromise; // Prevent duplicate requests
    }
    
    tagsPromise = fetch('/api/datasets/tags')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            cachedTags = data.tags || [];
            tagsPromise = null;
            return cachedTags;
        })
        .catch(error => {
            console.error('Failed to fetch tags:', error);
            tagsPromise = null;
            return cachedTags; // Fallback to cached value
        });
    
    return tagsPromise;
}

// Initialize tags on page load
fetchAvailableTags();
```

### 2. Update Completion Provider

Modify the completion provider to use async tags:

```typescript
monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['"', "'"],
    
    async provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        const tagsContainsMatch = textUntilPosition.match(/tags\.contains\(["']$/);
        
        if (tagsContainsMatch) {
            // Fetch tags asynchronously
            const tags = await fetchAvailableTags();
            
            const wordInfo = model.getWordUntilPosition(position);
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: wordInfo.startColumn,
                endColumn: wordInfo.endColumn
            };
            
            const suggestions: monaco.languages.CompletionItem[] = tags.map(tag => ({
                label: tag,
                kind: monaco.languages.CompletionItemKind.Value,
                detail: 'Available tag',
                documentation: `Filter samples with tag: "${tag}"`,
                insertText: tag,
                range: range
            }));
            
            return { suggestions };
        }
        
        return { suggestions: [] };
    }
});
```

### 3. Periodic Refresh

Keep tags up-to-date by refreshing periodically:

```typescript
// Refresh tags every 60 seconds
setInterval(() => {
    fetchAvailableTags();
}, 60000);

// Or use visibility API to refresh when tab becomes visible
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        fetchAvailableTags();
    }
});
```

## Advanced Patterns

### Context-Aware Suggestions

Different fields might have different valid values:

```typescript
interface FieldSuggestions {
    tags: string[];
    labels: string[];
    formats: string[];
}

let fieldSuggestions: FieldSuggestions = {
    tags: [],
    labels: [],
    formats: []
};

async function fetchFieldSuggestions(): Promise<FieldSuggestions> {
    const response = await fetch('/api/datasets/field-suggestions');
    const data = await response.json();
    fieldSuggestions = data;
    return data;
}

monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['"', "'"],
    
    async provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        let suggestions: monaco.languages.CompletionItem[] = [];
        const wordInfo = model.getWordUntilPosition(position);
        const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: wordInfo.startColumn,
            endColumn: wordInfo.endColumn
        };
        
        // Tags autocomplete
        if (textUntilPosition.match(/tags\.contains\(["']$/)) {
            const tags = await fetchFieldSuggestions();
            suggestions = tags.tags.map(tag => ({
                label: tag,
                kind: monaco.languages.CompletionItemKind.Value,
                detail: 'Tag',
                insertText: tag,
                range
            }));
        }
        
        // Label autocomplete
        else if (textUntilPosition.match(/label\s*==\s*["']$/)) {
            const data = await fetchFieldSuggestions();
            suggestions = data.labels.map(label => ({
                label: label,
                kind: monaco.languages.CompletionItemKind.Value,
                detail: 'Object label',
                insertText: label,
                range
            }));
        }
        
        // Format autocomplete
        else if (textUntilPosition.match(/format\s*==\s*["']$/)) {
            const data = await fetchFieldSuggestions();
            suggestions = data.formats.map(format => ({
                label: format,
                kind: monaco.languages.CompletionItemKind.Value,
                detail: 'Image format',
                insertText: format,
                range
            }));
        }
        
        return { suggestions };
    }
});
```

### Dataset-Specific Suggestions

Fetch suggestions based on the current dataset:

```typescript
let currentDatasetId: string | null = null;

function setCurrentDataset(datasetId: string) {
    currentDatasetId = datasetId;
    // Clear cache when dataset changes
    cachedTags = [];
    fetchAvailableTags();
}

async function fetchAvailableTags(): Promise<string[]> {
    if (!currentDatasetId) {
        return [];
    }
    
    const response = await fetch(`/api/datasets/${currentDatasetId}/tags`);
    const data = await response.json();
    cachedTags = data.tags;
    return cachedTags;
}
```

### Fuzzy Filtering

Add client-side fuzzy matching for better UX:

```typescript
function fuzzyMatch(pattern: string, str: string): boolean {
    pattern = pattern.toLowerCase();
    str = str.toLowerCase();
    
    let patternIdx = 0;
    let strIdx = 0;
    
    while (patternIdx < pattern.length && strIdx < str.length) {
        if (pattern[patternIdx] === str[strIdx]) {
            patternIdx++;
        }
        strIdx++;
    }
    
    return patternIdx === pattern.length;
}

monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['"', "'"],
    
    async provideCompletionItems(model, position) {
        // ... detect context ...
        
        if (tagsContainsMatch) {
            const tags = await fetchAvailableTags();
            
            // Get current input after the quote
            const afterQuote = lineContent.substring(position.column - 1);
            const currentInput = afterQuote.match(/^([^"']*)/)?.[1] || '';
            
            // Filter tags using fuzzy matching
            const filteredTags = currentInput
                ? tags.filter(tag => fuzzyMatch(currentInput, tag))
                : tags;
            
            const suggestions = filteredTags.map(tag => ({
                label: tag,
                kind: monaco.languages.CompletionItemKind.Value,
                detail: 'Available tag',
                insertText: tag,
                range
            }));
            
            return { suggestions };
        }
        
        return { suggestions: [] };
    }
});
```

## API Response Format

Expected JSON response from `/api/datasets/tags`:

```json
{
    "tags": [
        "reviewed",
        "needs-labeling",
        "approved",
        "rejected"
    ]
}
```

Or for multiple fields:

```json
{
    "tags": ["reviewed", "approved"],
    "labels": ["cat", "dog", "person"],
    "formats": ["png", "jpeg", "webp"]
}
```

## Error Handling

Always provide fallbacks:

```typescript
async function fetchAvailableTags(): Promise<string[]> {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout
        
        const response = await fetch('/api/datasets/tags', {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        cachedTags = data.tags || [];
        return cachedTags;
        
    } catch (error) {
        console.error('Failed to fetch tags:', error);
        
        // Fallback to cached tags or defaults
        return cachedTags.length > 0 
            ? cachedTags 
            : ['reviewed', 'needs-labeling']; // minimal defaults
    }
}
```

## Performance Tips

1. **Debounce API calls**: Use caching to avoid excessive requests
2. **Lazy loading**: Only fetch when autocomplete is triggered
3. **Prefetch**: Load tags on editor initialization
4. **Background refresh**: Update cache without blocking UI
5. **IndexedDB**: Cache tags locally for offline support

## Example: Complete Integration

```typescript
// Complete example with all features
class TagSuggestionManager {
    private cache: Map<string, string[]> = new Map();
    private pendingRequests: Map<string, Promise<string[]>> = new Map();
    
    constructor(private baseUrl: string) {}
    
    async getTags(datasetId: string): Promise<string[]> {
        // Return from cache if available
        if (this.cache.has(datasetId)) {
            return this.cache.get(datasetId)!;
        }
        
        // Return pending request if in progress
        if (this.pendingRequests.has(datasetId)) {
            return this.pendingRequests.get(datasetId)!;
        }
        
        // Start new request
        const request = this.fetchTags(datasetId);
        this.pendingRequests.set(datasetId, request);
        
        try {
            const tags = await request;
            this.cache.set(datasetId, tags);
            return tags;
        } finally {
            this.pendingRequests.delete(datasetId);
        }
    }
    
    private async fetchTags(datasetId: string): Promise<string[]> {
        const response = await fetch(`${this.baseUrl}/datasets/${datasetId}/tags`);
        const data = await response.json();
        return data.tags || [];
    }
    
    clearCache() {
        this.cache.clear();
    }
    
    invalidateDataset(datasetId: string) {
        this.cache.delete(datasetId);
    }
}

// Usage
const tagManager = new TagSuggestionManager('/api');

monaco.languages.registerCompletionItemProvider('lightly-query', {
    triggerCharacters: ['"', "'"],
    
    async provideCompletionItems(model, position) {
        const lineContent = model.getLineContent(position.lineNumber);
        const textUntilPosition = lineContent.substring(0, position.column - 1);
        
        if (textUntilPosition.match(/tags\.contains\(["']$/)) {
            const tags = await tagManager.getTags('current-dataset-id');
            
            const wordInfo = model.getWordUntilPosition(position);
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: wordInfo.startColumn,
                endColumn: wordInfo.endColumn
            };
            
            const suggestions = tags.map(tag => ({
                label: tag,
                kind: monaco.languages.CompletionItemKind.Value,
                detail: 'Available tag',
                insertText: tag,
                range
            }));
            
            return { suggestions };
        }
        
        return { suggestions: [] };
    }
});
```

## Testing

Test your autocomplete with:

1. **Unit tests**: Mock fetch responses
2. **Integration tests**: Use MSW (Mock Service Worker)
3. **Manual testing**: 
   - Type `ImageSampleField.tags.contains("`
   - Verify suggestions appear
   - Test with slow/failed API responses

## See Also

- [Monaco Editor Completion API](https://microsoft.github.io/monaco-editor/api/interfaces/monaco.languages.CompletionItemProvider.html)
- [main.ts](./src/main.ts) - Current implementation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
