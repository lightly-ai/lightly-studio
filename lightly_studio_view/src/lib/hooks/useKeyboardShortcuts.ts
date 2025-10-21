import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import { page } from '$app/stores';
import { useSettings } from '$lib/hooks/useSettings';
import { routeHelpers } from '$lib/routes';
import { onDestroy, onMount } from 'svelte';
import { get } from 'svelte/store';

export type KeyboardShortcut = {
    key: string;
    action: (event: KeyboardEvent) => void;
    description: string;
    // For future extension when we add UI configuration
    isConfigurable?: boolean;
    requiredPath?: RegExp | ((path: string) => boolean);
};

export const useKeyboardShortcuts = (shortcuts: Record<string, KeyboardShortcut>) => {
    // Get keyboard shortcuts from the settings store
    const { settingsStore } = useSettings();

    // No need to initialize settings here - that should be done at the app level

    // Track pressed keys
    const pressedKeys = new Set<string>();

    // Handle key down events
    const handleKeyDown = (event: KeyboardEvent) => {
        // Don't trigger shortcuts when typing in input fields
        if (
            event.target instanceof HTMLInputElement ||
            event.target instanceof HTMLTextAreaElement ||
            event.target instanceof HTMLSelectElement
        ) {
            return;
        }

        pressedKeys.add(event.key);

        // Check if any registered shortcut matches the pressed key
        const currentPath = get(page).url.pathname;

        // Create a mapping from shortcut IDs to configured keys
        const mappings: Record<string, string> = {
            hideAnnotations: get(settingsStore).key_hide_annotations || 'v',
            goBack: get(settingsStore).key_go_back || 'Escape'
        };

        Object.entries(shortcuts).forEach(([id, shortcut]) => {
            // Get the configured key for this shortcut (or fall back to default)
            const configuredKey = mappings[id] || shortcut.key;

            if (event.key === configuredKey) {
                // Check if path requirement is met (if specified)
                if (shortcut.requiredPath) {
                    if (typeof shortcut.requiredPath === 'function') {
                        if (!shortcut.requiredPath(currentPath)) {
                            return;
                        }
                    } else if (!shortcut.requiredPath.test(currentPath)) {
                        return;
                    }
                }

                shortcut.action(event);
            }
        });
    };

    // Handle key up events
    const handleKeyUp = (event: KeyboardEvent) => {
        pressedKeys.delete(event.key);
    };

    // Setup event listeners
    onMount(() => {
        if (browser) {
            window.addEventListener('keydown', handleKeyDown);
            window.addEventListener('keyup', handleKeyUp);
        }
    });

    // Clean up event listeners
    onDestroy(() => {
        if (browser) {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        }
    });

    return {
        // Allow checking if a key is currently pressed
        isKeyPressed: (key: string) => pressedKeys.has(key)
    };
};

// Define default shortcut mappings
export const defaultShortcuts: Record<string, KeyboardShortcut> = {
    goBack: {
        key: 'Escape',
        description: 'Go back from detail view to grid view',
        isConfigurable: true,
        // Support paths like /samples/[sample_id] and /datasets/[dataset_id]/samples/[sample_id]
        requiredPath: (path: string) => {
            // Match both dataset details and standalone sample details
            return (
                /\/datasets\/[^/]+\/(samples|annotations)\/[^/]+/.test(path) ||
                /\/samples\/[^/]+/.test(path)
            );
        },
        action: () => {
            const currentPath = get(page).url.pathname;
            const datasetId = get(page).params.dataset_id;

            // Check if we're in a sample detail view without dataset context
            if (/\/samples\/[^/]+/.test(currentPath) && !datasetId) {
                // Go back to the samples list or navigate to home
                goto('/');
                return;
            }

            if (!datasetId) return;

            // Determine if we're in samples or annotations detail view
            if (currentPath.includes('/samples/')) {
                goto(routeHelpers.toSamples(datasetId));
            } else if (currentPath.includes('/annotations/')) {
                goto(routeHelpers.toAnnotations(datasetId));
            }
        }
    },
    hideAnnotations: {
        key: 'v',
        description: 'Temporarily hide annotations while key is pressed',
        isConfigurable: true,
        action: () => {
            // The actual implementation will be handled by the component
            // that subscribes to the hideAnnotations store
        }
    }
};
