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
    const validTotal = $derived(Math.max(1, total));
    const percentage = $derived(Math.round((validCurrent / validTotal) * 100));

    const stateConfig = {
        pending: {
            label: 'Pending',
            color: 'bg-gray-400',
            textColor: 'text-gray-600 dark:text-gray-400'
        },
        indexing: {
            label: 'Indexing',
            color: 'bg-blue-500',
            textColor: 'text-blue-600 dark:text-blue-400'
        },
        embedding: {
            label: 'Processing',
            color: 'bg-purple-500',
            textColor: 'text-purple-600 dark:text-purple-400'
        },
        ready: {
            label: 'Ready',
            color: 'bg-green-500',
            textColor: 'text-green-600 dark:text-green-400'
        },
        error: {
            label: 'Error',
            color: 'bg-red-500',
            textColor: 'text-red-600 dark:text-red-400'
        }
    };

    const config = $derived(stateConfig[state]);
</script>

<div class="dataset-progress-compact flex items-center gap-2">
    <!-- Icon/Spinner -->
    {#if state === 'indexing' || state === 'embedding'}
        <div class="spinner-sm"></div>
    {:else if state === 'ready'}
        <svg class="w-3 h-3 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
        </svg>
    {:else if state === 'error'}
        <svg class="w-3 h-3 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
    {/if}

    <!-- Progress Info -->
    <div class="flex flex-col gap-0.5 min-w-0 flex-1">
        <div class="flex items-center gap-2 justify-between">
            <span class={`text-xs font-medium ${config.textColor} truncate`}>
                {config.label}
            </span>
            {#if state !== 'pending' && state !== 'ready' && state !== 'error'}
                <span class="text-xs text-gray-500 dark:text-gray-400 font-mono tabular-nums">
                    {percentage}%
                </span>
            {/if}
        </div>

        <!-- Compact Progress Bar -->
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1 overflow-hidden">
            <div
                class={`${config.color} h-1 rounded-full transition-all duration-300 ease-out ${
                    state !== 'ready' && state !== 'error' ? 'progress-animated-sm' : ''
                }`}
                style={`width: ${state === 'ready' ? 100 : state === 'error' ? 0 : percentage}%`}
            ></div>
        </div>
    </div>
</div>

<style>
    .spinner-sm {
        width: 12px;
        height: 12px;
        border: 2px solid transparent;
        border-top-color: currentColor;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        flex-shrink: 0;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .progress-animated-sm {
        position: relative;
        overflow: hidden;
    }

    .progress-animated-sm::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        right: 0;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.4),
            transparent
        );
        animation: shimmer 1.5s infinite;
    }

    @keyframes shimmer {
        0% {
            transform: translateX(-100%);
        }
        100% {
            transform: translateX(100%);
        }
    }
</style>
