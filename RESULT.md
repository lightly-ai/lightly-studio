# Scalable Dataset Loading: Three-Step Architecture

## Problem
Loading large datasets was blocking and slow:
- 10,000 images took 60-180 seconds with no feedback
- Users had to wait for everything (metadata + embeddings) to complete
- No progress indication during loading
- Application startup was blocked by dataset loading

## Solution: Fast Startup with Background Processing

### Step 1: Fast Indexing (Immediate)
- Scan filesystem for filenames only
- Store file paths in database
- **Result:** UI becomes available immediately, images can render

### Step 2: Indexing with Metadata (Background Task)
- Extract image metadata (width, height, format)
- Process annotations if provided
- Store complete metadata in database
- **Result:** Dataset is fully indexed and browsable

### Step 3: Processing Embeddings (Background Task)
- Load embedding model
- Generate ML embeddings in batches
- Store embeddings for similarity search
- **Result:** All features enabled (similarity search, clustering, etc.)

**Key Improvement:** Application starts immediately with fast filename indexing. UI is accessible while metadata extraction and embedding calculation run in the background. Users see real-time progress for all background tasks.

## Architecture Diagram

```mermaid
sequenceDiagram
    actor User
    participant App as Application
    participant UI as User Interface
    participant BG1 as Background Worker<br/>(Indexing)
    participant BG2 as Background Worker<br/>(Embeddings)
    participant DB as Database

    User->>App: Start Application
    App->>DB: Fast Indexing<br/>(filenames only)
    DB-->>App: Paths stored
    App->>UI: UI Available ✓
    Note over UI: Images can render immediately

    par Parallel Background Processing
        App->>BG1: Start Indexing Task
        BG1->>DB: Extract metadata<br/>(width, height)
        BG1->>DB: Process annotations
        loop Progress Updates
            BG1-->>UI: Indexing progress
        end
        BG1-->>UI: Indexing complete ✓
    and
        App->>BG2: Start Processing Task
        BG2->>BG2: Load embedding model
        BG2->>DB: Generate embeddings<br/>(batch processing)
        loop Progress Updates
            BG2-->>UI: Processing progress
        end
        BG2-->>UI: Processing complete ✓
    end

    Note over UI: All features enabled
```

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Application Startup** | Blocked by dataset loading | Instant startup |
| **UI Availability** | Wait 60-180s | Immediate (<1s) |
| **User Feedback** | No progress indication | Real-time progress tracking |
| **Usability** | Wait for everything | Use dataset while processing |
| **Parallelization** | Sequential operations | Independent background tasks |

## Impact

✅ **Instant Application Startup:** App starts in <1 second with fast filename indexing

✅ **UI Available Immediately:** Users can see and interact with images right away

✅ **Real-Time Progress Tracking:** UI shows progress for all background tasks

✅ **Better UX:** Clear separation between "UI ready" → "indexed" → "embeddings ready"

✅ **Resource Optimization:** Heavy operations (metadata, embeddings) happen in background

✅ **Non-blocking Operations:** All heavy processing separated from application lifecycle
