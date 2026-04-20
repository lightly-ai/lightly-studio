<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import CollectionLayout from './CollectionLayout.svelte';
    import { Search, SlidersHorizontal, BarChart3 } from '@lucide/svelte';

    const { Story } = defineMeta({
        title: 'Components/CollectionLayout',
        component: CollectionLayout,
        tags: ['autodocs'],
        argTypes: {
            showDetails: {
                control: 'boolean',
                description: 'Shows detail view instead of grid view'
            },
            showLeftSidebar: {
                control: 'boolean',
                description: 'Shows the left sidebar with filters'
            },
            showWithPlot: {
                control: 'boolean',
                description: 'Shows the plot panel alongside the grid'
            },
            showGridHeader: {
                control: 'boolean',
                description: 'Shows the grid header with search bar'
            },
            showSelectionPill: {
                control: 'boolean',
                description: 'Shows the selection pill at bottom'
            },
            selectedCount: {
                control: 'number',
                description: 'Number of selected items'
            }
        }
    });
</script>

<Story
    name="Basic Layout"
    args={{
        showDetails: false,
        showLeftSidebar: true,
        showWithPlot: false,
        showGridHeader: true,
        showSelectionPill: true,
        selectedCount: 0
    }}
>
    {#snippet children({
        showDetails,
        showLeftSidebar,
        showWithPlot,
        showGridHeader,
        showSelectionPill,
        selectedCount
    })}
        <CollectionLayout
            {showDetails}
            {showLeftSidebar}
            {showWithPlot}
            {showGridHeader}
            {showSelectionPill}
            {selectedCount}
            onClearSelection={() => console.log('Clear selection')}
        >
            {#snippet header()}
                <div class="flex items-center justify-between border-b bg-card p-4">
                    <h1 class="text-2xl font-bold">Collection Header</h1>
                    <div class="flex items-center gap-2">
                        <span class="text-sm text-muted-foreground">128 samples</span>
                    </div>
                </div>
            {/snippet}

            {#snippet sidebar()}
                <div class="space-y-4">
                    <div class="space-y-2">
                        <div class="flex items-center gap-2">
                            <SlidersHorizontal class="h-4 w-4" />
                            <h3 class="font-semibold">Filters</h3>
                        </div>
                        <div class="space-y-2">
                            <label class="flex items-center gap-2">
                                <input type="checkbox" class="rounded" />
                                <span class="text-sm">Category A (45)</span>
                            </label>
                            <label class="flex items-center gap-2">
                                <input type="checkbox" class="rounded" />
                                <span class="text-sm">Category B (32)</span>
                            </label>
                            <label class="flex items-center gap-2">
                                <input type="checkbox" class="rounded" />
                                <span class="text-sm">Category C (51)</span>
                            </label>
                        </div>
                    </div>
                    <div class="border-t pt-4">
                        <h3 class="mb-2 font-semibold">Metadata</h3>
                        <div class="space-y-1 text-sm text-muted-foreground">
                            <p>Width: 224-1024px</p>
                            <p>Height: 224-768px</p>
                            <p>Format: JPEG, PNG</p>
                        </div>
                    </div>
                </div>
            {/snippet}

            {#snippet searchBar()}
                <div class="flex flex-1 items-center gap-2 rounded-lg border px-3 py-2">
                    <Search class="h-4 w-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search by text or image..."
                        class="flex-1 bg-transparent outline-none"
                    />
                </div>
            {/snippet}

            {#snippet auxControls()}
                <button
                    class="rounded-lg border px-3 py-2 transition-colors hover:bg-accent"
                    onclick={() => console.log('Toggle plot')}
                >
                    <BarChart3 class="h-4 w-4" />
                </button>
            {/snippet}

            {#snippet footer()}
                <div class="flex items-center justify-between border-t bg-card px-4 py-2 text-sm">
                    <span class="text-muted-foreground">128 samples | 456 annotations</span>
                    <span class="text-muted-foreground">Filtered: 64 samples | 234 annotations</span
                    >
                </div>
            {/snippet}

            <!-- Main content -->
            <div class="grid grid-cols-4 gap-4 overflow-auto p-2">
                {#each Array(16) as _, i}
                    <div
                        class="aspect-square rounded-lg border bg-muted transition-all hover:scale-105"
                    >
                        <div class="flex h-full items-center justify-center text-muted-foreground">
                            Sample {i + 1}
                        </div>
                    </div>
                {/each}
            </div>
        </CollectionLayout>
    {/snippet}
</Story>

<Story
    name="With Plot Panel"
    args={{
        showDetails: false,
        showLeftSidebar: true,
        showWithPlot: true,
        showGridHeader: true,
        showSelectionPill: true,
        selectedCount: 5
    }}
>
    {#snippet children({
        showDetails,
        showLeftSidebar,
        showWithPlot,
        showGridHeader,
        showSelectionPill,
        selectedCount
    })}
        <CollectionLayout
            {showDetails}
            {showLeftSidebar}
            {showWithPlot}
            {showGridHeader}
            {showSelectionPill}
            {selectedCount}
            onClearSelection={() => console.log('Clear selection')}
        >
            {#snippet header()}
                <div class="flex items-center justify-between border-b bg-card p-4">
                    <h1 class="text-2xl font-bold">Collection with Embeddings</h1>
                </div>
            {/snippet}

            {#snippet sidebar()}
                <div class="space-y-4">
                    <h3 class="font-semibold">Labels</h3>
                    <div class="space-y-2">
                        <label class="flex items-center gap-2">
                            <input type="checkbox" checked class="rounded" />
                            <span class="text-sm">Dog (12)</span>
                        </label>
                        <label class="flex items-center gap-2">
                            <input type="checkbox" checked class="rounded" />
                            <span class="text-sm">Cat (8)</span>
                        </label>
                    </div>
                </div>
            {/snippet}

            {#snippet searchBar()}
                <div class="flex flex-1 items-center gap-2 rounded-lg border px-3 py-2">
                    <Search class="h-4 w-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search embeddings..."
                        class="flex-1 bg-transparent outline-none"
                    />
                </div>
            {/snippet}

            {#snippet plotPanel()}
                <div class="flex h-full flex-col rounded-[1vw] bg-card p-4">
                    <h3 class="mb-4 font-semibold">Embedding Plot</h3>
                    <div class="flex flex-1 items-center justify-center rounded-lg bg-muted">
                        <p class="text-muted-foreground">2D Embedding Visualization</p>
                    </div>
                </div>
            {/snippet}

            {#snippet footer()}
                <div class="border-t bg-card px-4 py-2 text-sm">
                    <span class="text-muted-foreground">5 samples selected</span>
                </div>
            {/snippet}

            <!-- Main content -->
            <div class="grid grid-cols-3 gap-4 overflow-auto p-2">
                {#each Array(12) as _, i}
                    <div
                        class="aspect-square rounded-lg border bg-muted transition-all hover:scale-105"
                        class:ring-2={i < 5}
                        class:ring-primary={i < 5}
                    >
                        <div class="flex h-full items-center justify-center text-muted-foreground">
                            Sample {i + 1}
                            {#if i < 5}
                                <span class="ml-1 text-primary">✓</span>
                            {/if}
                        </div>
                    </div>
                {/each}
            </div>
        </CollectionLayout>
    {/snippet}
</Story>

<Story
    name="Detail View"
    args={{
        showDetails: true,
        showLeftSidebar: false,
        showWithPlot: false,
        showGridHeader: false,
        showSelectionPill: false,
        selectedCount: 0
    }}
>
    {#snippet children({
        showDetails,
        showLeftSidebar,
        showWithPlot,
        showGridHeader,
        showSelectionPill,
        selectedCount
    })}
        <CollectionLayout
            {showDetails}
            {showLeftSidebar}
            {showWithPlot}
            {showGridHeader}
            {showSelectionPill}
            {selectedCount}
            onClearSelection={() => console.log('Clear selection')}
        >
            {#snippet header()}
                <div class="flex items-center gap-4 border-b bg-card p-4">
                    <button
                        class="rounded-lg px-3 py-2 transition-colors hover:bg-accent"
                        onclick={() => console.log('Back')}
                    >
                        ← Back
                    </button>
                    <h1 class="text-2xl font-bold">Sample Details</h1>
                </div>
            {/snippet}

            <!-- Detail content -->
            <div class="flex h-full items-center justify-center p-8">
                <div class="max-w-4xl space-y-4">
                    <div class="aspect-video w-full rounded-lg bg-muted"></div>
                    <div class="space-y-2">
                        <h2 class="text-xl font-semibold">Sample_001.jpg</h2>
                        <div class="space-y-1 text-sm text-muted-foreground">
                            <p>Size: 1024x768px</p>
                            <p>Format: JPEG</p>
                            <p>Created: 2024-01-15</p>
                        </div>
                    </div>
                </div>
            </div>
        </CollectionLayout>
    {/snippet}
</Story>

<Story
    name="Minimal Layout"
    args={{
        showDetails: false,
        showLeftSidebar: false,
        showWithPlot: false,
        showGridHeader: false,
        showSelectionPill: false,
        selectedCount: 0
    }}
>
    {#snippet children({
        showDetails,
        showLeftSidebar,
        showWithPlot,
        showGridHeader,
        showSelectionPill,
        selectedCount
    })}
        <CollectionLayout
            {showDetails}
            {showLeftSidebar}
            {showWithPlot}
            {showGridHeader}
            {showSelectionPill}
            {selectedCount}
            onClearSelection={() => console.log('Clear selection')}
        >
            {#snippet header()}
                <div class="border-b bg-card p-4">
                    <h1 class="text-xl font-bold">Minimal View</h1>
                </div>
            {/snippet}

            <!-- Main content -->
            <div class="flex items-center justify-center p-8">
                <div class="text-center">
                    <h2 class="mb-4 text-2xl text-muted-foreground">No filters, no plot</h2>
                    <p class="text-muted-foreground">Just the content area</p>
                </div>
            </div>
        </CollectionLayout>
    {/snippet}
</Story>

<Story
    name="With All Sections"
    args={{
        showDetails: false,
        showLeftSidebar: true,
        showWithPlot: false,
        showGridHeader: true,
        showSelectionPill: true,
        selectedCount: 12
    }}
>
    {#snippet children({
        showDetails,
        showLeftSidebar,
        showWithPlot,
        showGridHeader,
        showSelectionPill,
        selectedCount
    })}
        <CollectionLayout
            {showDetails}
            {showLeftSidebar}
            {showWithPlot}
            {showGridHeader}
            {showSelectionPill}
            {selectedCount}
            onClearSelection={() => console.log('Clear selection')}
        >
            {#snippet header()}
                <div class="flex items-center justify-between border-b bg-card p-4">
                    <h1 class="text-2xl font-bold">Full Featured Layout</h1>
                    <div class="flex items-center gap-2">
                        <button class="rounded-lg px-3 py-2 hover:bg-accent">Export</button>
                        <button class="rounded-lg bg-primary px-3 py-2 text-primary-foreground">
                            Create Model
                        </button>
                    </div>
                </div>
            {/snippet}

            {#snippet sidebar()}
                <div class="space-y-4">
                    <div>
                        <h3 class="mb-2 font-semibold">Tags</h3>
                        <div class="flex flex-wrap gap-2">
                            <span class="rounded bg-primary/10 px-2 py-1 text-xs text-primary"
                                >validated</span
                            >
                            <span class="rounded bg-primary/10 px-2 py-1 text-xs text-primary"
                                >high-quality</span
                            >
                        </div>
                    </div>
                    <div>
                        <h3 class="mb-2 font-semibold">Labels</h3>
                        <div class="space-y-2">
                            {#each ['Dog', 'Cat', 'Bird', 'Car'] as label, i}
                                <label class="flex items-center gap-2">
                                    <input type="checkbox" checked={i < 2} class="rounded" />
                                    <span class="text-sm">{label} ({10 + i * 5})</span>
                                </label>
                            {/each}
                        </div>
                    </div>
                    <div>
                        <h3 class="mb-2 font-semibold">Dimensions</h3>
                        <div class="space-y-2">
                            <div>
                                <label class="mb-1 block text-xs text-muted-foreground">Width</label
                                >
                                <input type="range" min="0" max="100" value="50" class="w-full" />
                            </div>
                            <div>
                                <label class="mb-1 block text-xs text-muted-foreground"
                                    >Height</label
                                >
                                <input type="range" min="0" max="100" value="70" class="w-full" />
                            </div>
                        </div>
                    </div>
                </div>
            {/snippet}

            {#snippet searchBar()}
                <div class="flex flex-1 items-center gap-2 rounded-lg border px-3 py-2">
                    <Search class="h-4 w-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search samples..."
                        class="flex-1 bg-transparent outline-none"
                    />
                </div>
            {/snippet}

            {#snippet auxControls()}
                <div class="flex items-center gap-2">
                    <button class="rounded-lg border px-3 py-2 transition-colors hover:bg-accent">
                        <BarChart3 class="h-4 w-4" />
                    </button>
                    <select class="rounded-lg border px-3 py-2 hover:bg-accent">
                        <option>Grid</option>
                        <option>List</option>
                    </select>
                </div>
            {/snippet}

            {#snippet fewShotDialogs()}
                <!-- Dialogs would render here -->
            {/snippet}

            {#snippet footer()}
                <div class="flex items-center justify-between border-t bg-card px-4 py-2 text-sm">
                    <div class="flex items-center gap-4">
                        <span class="text-muted-foreground">Total: 128 samples</span>
                        <span class="text-muted-foreground">|</span>
                        <span class="text-muted-foreground">456 annotations</span>
                    </div>
                    <div class="flex items-center gap-4">
                        <span>Filtered: 64 samples</span>
                        <span class="text-muted-foreground">|</span>
                        <span>234 annotations</span>
                    </div>
                </div>
            {/snippet}

            <!-- Main content -->
            <div class="grid grid-cols-4 gap-4 overflow-auto p-2">
                {#each Array(24) as _, i}
                    <div
                        class="aspect-square rounded-lg border bg-muted transition-all hover:scale-105"
                        class:ring-2={i < 12}
                        class:ring-primary={i < 12}
                    >
                        <div class="flex h-full items-center justify-center text-muted-foreground">
                            {#if i < 12}
                                <span class="font-semibold text-primary">✓ {i + 1}</span>
                            {:else}
                                Sample {i + 1}
                            {/if}
                        </div>
                    </div>
                {/each}
            </div>
        </CollectionLayout>
    {/snippet}
</Story>
