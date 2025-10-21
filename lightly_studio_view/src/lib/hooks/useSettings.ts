import type { components } from '$lib/schema';
import { client } from '$lib/services/dataset';
import { derived, get, writable } from 'svelte/store';
import { getSettings } from '$lib/api/lightly_studio_local';

type SettingView = components['schemas']['SettingView'];
type UpdateSettingsResult = { success: boolean; error?: string };

// Default settings values
const DEFAULT_SETTINGS: SettingView = {
    setting_id: '00000000-0000-0000-0000-000000000000',
    grid_view_sample_rendering: 'contain',
    key_hide_annotations: 'v',
    key_go_back: 'Escape',
    show_annotation_text_labels: true,
    show_sample_filenames: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
};

// Create stores for settings state
const settingsStore = writable<SettingView>(DEFAULT_SETTINGS);
const isLoadingStore = writable(false);
const errorStore = writable<string | null>(null);
const isLoadedStore = writable(false);

// Derived stores for convenience
const gridViewSampleRenderingStore = derived(
    settingsStore,
    ($settings) => $settings.grid_view_sample_rendering || 'contain'
);

const showAnnotationTextLabelsStore = derived(
    settingsStore,
    ($settings) => $settings.show_annotation_text_labels ?? true
);

const showSampleFilenamesStore = derived(
    settingsStore,
    ($settings) => $settings.show_sample_filenames ?? true
);

// Initialize settings by loading from API
const initSettings = async () => {
    // Always set default settings first
    settingsStore.set(DEFAULT_SETTINGS);

    if (get(isLoadedStore) || get(isLoadingStore)) return;

    isLoadingStore.set(true);
    errorStore.set(null);

    try {
        const { data } = await getSettings();
        if (data) {
            settingsStore.set(data as unknown as SettingView);
            isLoadedStore.set(true);
        }
    } catch (err) {
        errorStore.set(String(err));
    } finally {
        isLoadingStore.set(false);
    }
};

// Save settings to the backend
const saveSettings = async (
    updatedSettings: Partial<SettingView>
): Promise<UpdateSettingsResult> => {
    isLoadingStore.set(true);
    errorStore.set(null);

    try {
        const currentSettings = get(settingsStore);

        // Create a fresh, clean settings object
        const newSettings: SettingView = {
            setting_id: currentSettings.setting_id || '',
            grid_view_sample_rendering:
                updatedSettings.grid_view_sample_rendering ||
                currentSettings.grid_view_sample_rendering ||
                'contain',
            key_hide_annotations:
                updatedSettings.key_hide_annotations || currentSettings.key_hide_annotations || 'v',
            key_go_back: updatedSettings.key_go_back || currentSettings.key_go_back || 'Escape',
            // This is important: use the value from updatedSettings if it exists
            show_annotation_text_labels:
                updatedSettings.show_annotation_text_labels !== undefined
                    ? updatedSettings.show_annotation_text_labels
                    : (currentSettings.show_annotation_text_labels ?? true),
            show_sample_filenames:
                updatedSettings.show_sample_filenames !== undefined
                    ? updatedSettings.show_sample_filenames
                    : (currentSettings.show_sample_filenames ?? true),
            created_at: currentSettings.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        // The API call
        const response = await client.POST('/api/settings', {
            body: newSettings,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.error) {
            const errorMsg = JSON.stringify(response.error);
            console.error('Settings API error:', errorMsg);
            errorStore.set(errorMsg);

            // We've already updated the local state, so we'll keep it
            // even though the API call failed

            return { success: false, error: errorMsg };
        }

        if (response.data) {
            settingsStore.set(response.data);
            return { success: true };
        }

        return { success: false, error: 'No data returned from API' };
    } catch (err) {
        const errorMsg = String(err);
        console.error('Error saving settings:', errorMsg);
        errorStore.set(errorMsg);

        return { success: false, error: errorMsg };
    } finally {
        isLoadingStore.set(false);
    }
};

// Utility function to update grid view rendering
const updateGridViewSampleRendering = async (
    rendering: components['schemas']['GridViewSampleRenderingType']
) => {
    return saveSettings({
        grid_view_sample_rendering: rendering
    });
};

// Updated function for annotation text labels
const updateShowAnnotationTextLabels = async (show: boolean) => {
    // Ensure we're working with a boolean
    const boolValue = Boolean(show);

    // Get current settings (after the store update in SettingsDialog)
    const currentSettings = get(settingsStore);

    // Create new settings with the explicit boolean value
    const newSettings = {
        ...currentSettings,
        show_annotation_text_labels: boolValue
    };

    // Send to API
    try {
        const response = await client.POST('/api/settings', {
            body: newSettings,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.error) {
            console.error('API error saving setting:', response.error);
            return { success: false, error: JSON.stringify(response.error) };
        }

        if (response.data) {
            // Update store with the response data
            settingsStore.set(response.data);
            return { success: true };
        }

        return { success: false, error: 'No data returned from API' };
    } catch (error) {
        console.error('Error saving annotation text label setting:', error);
        return { success: false, error: String(error) };
    }
};

// Export the settings store and functions
export function useSettings() {
    // Initialize settings on first use
    if (!get(isLoadedStore) && !get(isLoadingStore)) {
        initSettings();
    }

    return {
        // State stores
        settingsStore,
        isLoadingStore,
        errorStore,
        isLoadedStore,

        // Derived stores
        gridViewSampleRenderingStore,
        showAnnotationTextLabelsStore,
        showSampleFilenamesStore,

        // Functions
        initSettings,
        saveSettings,
        updateGridViewSampleRendering,
        updateShowAnnotationTextLabels,

        // Direct access to current values
        get settings() {
            return get(settingsStore);
        },
        get isLoading() {
            return get(isLoadingStore);
        },
        get error() {
            return get(errorStore);
        },
        get isLoaded() {
            return get(isLoadedStore);
        }
    };
}
