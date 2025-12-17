<script lang="ts">
    import type { DatasetProgressState } from './types';

    const {
        state,
        current = 0,
        total = 100,
        message = '',
        error = null
    }: {
        state: DatasetProgressState;
        current?: number;
        total?: number;
        message?: string;
        error?: string | null;
    } = $props();

    // Validate and clamp values
    const validCurrent = $derived(Math.max(0, Math.min(current, total)));
    const validTotal = $derived(Math.max(1, total)); // Ensure total is at least 1
    const percentage = $derived(Math.round((validCurrent / validTotal) * 100));

    const stateConfig = {
        pending: {
            label: 'Pending',
            color: 'bg-gray-400',
            textColor: 'text-gray-600'
        },
        indexing: {
            label: 'Indexing',
            color: 'bg-blue-500',
            textColor: 'text-blue-600'
        },
        embedding: {
            label: 'Generating Embeddings',
            color: 'bg-purple-500',
            textColor: 'text-purple-600'
        },
        ready: {
            label: 'Ready',
            color: 'bg-green-500',
            textColor: 'text-green-600'
        },
        error: {
            label: 'Error',
            color: 'bg-red-500',
            textColor: 'text-red-600'
        }
    };

    const config = $derived(stateConfig[state]);
</script>

<div class="dataset-progress w-full">
    <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
            {#if state === 'indexing' || state === 'embedding'}
                <div class="spinner"></div>
            {:else if state === 'ready'}
                <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
            {:else if state === 'error'}
                <svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            {/if}
            <span class={`text-sm font-medium ${config.textColor}`}>
                {config.label}
            </span>
        </div>
        {#if state !== 'pending' && state !== 'ready' && state !== 'error'}
            <span class="text-sm text-gray-600 dark:text-gray-400 font-mono">
                {percentage}% ({validCurrent}/{validTotal})
            </span>
        {/if}
    </div>

    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden shadow-inner">
        <div
            class={`${config.color} h-2.5 rounded-full transition-all duration-300 ease-out ${
                state !== 'ready' && state !== 'error' ? 'progress-animated' : ''
            } ${state === 'ready' ? 'pulse-once' : ''}`}
            style={`width: ${state === 'ready' ? 100 : state === 'error' ? 0 : percentage}%`}
        ></div>
    </div>

    {#if message}
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-2 fade-in">{message}</p>
    {/if}

    {#if error}
        <div class="flex items-start gap-2 mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded fade-in">
            <svg class="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <p class="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
    {/if}
</div>

<style>
    .progress-animated {
        position: relative;
        overflow: hidden;
    }

    .progress-animated::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        right: 0;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.3),
            transparent
        );
        animation: shimmer 2s infinite;
    }

    @keyframes shimmer {
        0% {
            transform: translateX(-100%);
        }
        100% {
            transform: translateX(100%);
        }
    }

    .pulse-once {
        animation: pulse-once 0.5s ease-out;
    }

    @keyframes pulse-once {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.7;
        }
    }

    .spinner {
        width: 14px;
        height: 14px;
        border: 2px solid transparent;
        border-top-color: currentColor;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .fade-in {
        animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
