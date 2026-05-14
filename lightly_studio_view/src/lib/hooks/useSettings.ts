import type { GridViewSampleRenderingType, SettingView } from '$lib/api/lightly_studio_local';
import { derived, get, writable } from 'svelte/store';
import { getSettings, setSettings } from '$lib/api/lightly_studio_local';

type UpdateSettingsResult = { success: boolean; error?: string };

// Default settings values
const DEFAULT_SETTINGS: SettingView = {
    setting_id: '00000000-0000-0000-0000-000000000000',
    grid_view_sample_rendering: 'contain',
    grid_view_thumbnail_quality: 'raw',
    key_hide_annotations: 'v',
    key_go_back: 'Escape',
    key_toggle_edit_mode: 'e',
    show_annotation_text_labels: false,
    show_sample_filenames: false,
    show_bounding_boxes_for_segmentation: true,
    created_at: new Date(),
    updated_at: new Date(),
    key_toolbar_selection: 's',
    key_toolbar_drag: 'd',
    key_toolbar_bounding_box: 'b',
    key_toolbar_segmentation_mask: 'm',
    key_toolbar_brush: 'r',
    key_toolbar_eraser: 'x'
};

// Create stores for settings state
const settingsStore = writable<SettingView>(DEFAULT_SETTINGS);
const isLoadingStore = writable(false);
const errorStore = writable<string | null>(null);
const isLoadedStore = writable(false);

// Derived stores for convenience
const gridViewSampleRenderingStore = derived(
    settingsStore,
    ($settings) => $settings.grid_view_sample_rendering
);

const showAnnotationTextLabelsStore = derived(
    settingsStore,
    ($settings) => $settings.show_annotation_text_labels
);

const showSampleFilenamesStore = derived(
    settingsStore,
    ($settings) => $settings.show_sample_filenames
);

const showBoundingBoxesForSegmentationStore = derived(
    settingsStore,
    ($settings) => $settings.show_bounding_boxes_for_segmentation
);

const gridViewThumbnailQualityStore = derived(
    settingsStore,
    ($settings) => $settings.grid_view_thumbnail_quality
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
            settingsStore.set(data);
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
        const newSettings: SettingView = {
            ...currentSettings,
            ...updatedSettings,
            updated_at: new Date()
        };

        const response = await setSettings({
            body: newSettings
        });

        if (response.error) {
            const errorMsg = JSON.stringify(response.error);
            console.error('Settings API error:', errorMsg);
            errorStore.set(errorMsg);
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
const updateGridViewSampleRendering = async (rendering: GridViewSampleRenderingType) => {
    return saveSettings({
        grid_view_sample_rendering: rendering
    });
};

// Utility function to update annotation text labels visibility
const updateShowAnnotationTextLabels = async (show: boolean) => {
    return saveSettings({
        show_annotation_text_labels: show
    });
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
        showBoundingBoxesForSegmentationStore,
        gridViewThumbnailQualityStore,

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
