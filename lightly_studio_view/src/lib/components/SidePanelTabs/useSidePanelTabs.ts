import { useGlobalStorage, usePostHog } from '$lib/hooks';

type PanelType = Parameters<ReturnType<typeof useGlobalStorage>['setActivePanel']>[0];

interface UseSidePanelTabsParams {
    getCollectionId: () => string;
}

export function useSidePanelTabs({ getCollectionId }: UseSidePanelTabsParams) {
    const { activePanel, setActivePanel } = useGlobalStorage();
    const { trackEvent } = usePostHog();

    function toggle(activePanel: PanelType | 'none', panel: PanelType) {
        const nextPanel = activePanel === panel ? 'none' : panel;
        setActivePanel(nextPanel);
        if (nextPanel !== 'none') {
            trackEvent('tool_panel_opened', {
                collection_id: getCollectionId(),
                panel_type: nextPanel
            });
        }
    }

    return { activePanel, toggle };
}
