<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import DatasetProgress from './DatasetProgress.svelte';
    import { useDatasetProgress, simulateProgress } from '$lib/hooks/useDatasetProgress';
    import type { DatasetProgressState } from './types';

    const {
        dataset_id = 'demo-dataset',
        mode = 'manual'
    }: {
        dataset_id?: string;
        mode?: 'polling' | 'websocket' | 'manual';
    } = $props();

    // Initialize progress hook
    const progressHook = useDatasetProgress({ dataset_id, mode });
    const { progress, startProgress, stopProgress, updateProgress, setError, isLoading } = progressHook;

    let simulationCleanup: (() => void) | null = null;

    // Demo controls
    function handleStartSimulation() {
        stopSimulation();
        simulationCleanup = simulateProgress(dataset_id);
    }

    function handleStartPolling() {
        startProgress();
    }

    function handleStop() {
        stopProgress();
        stopSimulation();
    }

    function handleSetState(state: DatasetProgressState) {
        if (state === 'error') {
            setError('Something went wrong!');
        } else {
            const values = {
                pending: { current: 0, total: 100, message: 'Waiting to start...' },
                indexing: { current: 30, total: 100, message: 'Indexing samples...' },
                embedding: { current: 70, total: 100, message: 'Generating embeddings...' },
                ready: { current: 100, total: 100, message: 'Dataset is ready!' }
            };
            const { current, total, message } = values[state];
            updateProgress(current, total, message);
        }
    }

    function stopSimulation() {
        if (simulationCleanup) {
            simulationCleanup();
            simulationCleanup = null;
        }
    }

    onDestroy(() => {
        stopProgress();
        stopSimulation();
    });
</script>

<div class="dataset-progress-demo p-6 space-y-6 bg-white dark:bg-gray-900 rounded-lg border">
    <div>
        <h2 class="text-2xl font-bold mb-2">Dataset Progress Demo</h2>
        <p class="text-gray-600 dark:text-gray-400">
            Dataset ID: <code class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">{dataset_id}</code>
        </p>
        <p class="text-gray-600 dark:text-gray-400">
            Mode: <code class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">{mode}</code>
        </p>
    </div>

    <!-- Progress Component -->
    <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        {#if $progress}
            <DatasetProgress
                state={$progress.state}
                current={$progress.current}
                total={$progress.total}
                message={$progress.message}
                error={$progress.error}
            />
        {:else}
            <p class="text-gray-500 dark:text-gray-400 text-center">No progress data available</p>
        {/if}
    </div>

    <!-- Demo Controls -->
    <div class="space-y-4">
        <div>
            <h3 class="text-lg font-semibold mb-2">Controls</h3>
            <div class="flex flex-wrap gap-2">
                <button
                    onclick={handleStartSimulation}
                    class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                    disabled={$isLoading}
                >
                    Start Simulation
                </button>

                {#if mode === 'polling'}
                    <button
                        onclick={handleStartPolling}
                        class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition"
                        disabled={$isLoading}
                    >
                        Start Polling
                    </button>
                {/if}

                <button
                    onclick={handleStop}
                    class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition"
                >
                    Stop
                </button>
            </div>
        </div>

        <div>
            <h3 class="text-lg font-semibold mb-2">Set State</h3>
            <div class="flex flex-wrap gap-2">
                <button
                    onclick={() => handleSetState('pending')}
                    class="px-3 py-1 bg-gray-400 text-white rounded hover:bg-gray-500 transition text-sm"
                >
                    Pending
                </button>
                <button
                    onclick={() => handleSetState('indexing')}
                    class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition text-sm"
                >
                    Indexing
                </button>
                <button
                    onclick={() => handleSetState('embedding')}
                    class="px-3 py-1 bg-purple-500 text-white rounded hover:bg-purple-600 transition text-sm"
                >
                    Embedding
                </button>
                <button
                    onclick={() => handleSetState('ready')}
                    class="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 transition text-sm"
                >
                    Ready
                </button>
                <button
                    onclick={() => handleSetState('error')}
                    class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 transition text-sm"
                >
                    Error
                </button>
            </div>
        </div>
    </div>

    <!-- Debug Info -->
    <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <h3 class="text-lg font-semibold mb-2">Debug Info</h3>
        <pre class="text-xs overflow-auto">{JSON.stringify($progress, null, 2)}</pre>
    </div>
</div>
