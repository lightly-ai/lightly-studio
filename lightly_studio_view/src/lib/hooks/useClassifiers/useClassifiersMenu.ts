import { writable, type Readable } from 'svelte/store';

interface UseClassifiersMenuReturn {
    isDialogOpen: Readable<boolean>;
    activeTab: Readable<string>;
    scrollToClassifierId: Readable<string | null>;
    openClassifiersMenu: () => void;
    closeClassifiersMenu: () => void;
    switchToManageTab: () => void;
    switchToCreateTab: () => void;
    scrollToAndSelectClassifier: (classifierId: string) => void;
}

const isDialogOpen = writable<boolean>(false);
const activeTab = writable<string>('create');
const scrollToClassifierId = writable<string | null>(null);

export function useClassifiersMenu(): UseClassifiersMenuReturn {
    const openClassifiersMenu = () => {
        isDialogOpen.set(true);
    };

    const closeClassifiersMenu = () => {
        isDialogOpen.set(false);
    };

    const switchToManageTab = () => {
        activeTab.set('manage');
    };

    const switchToCreateTab = () => {
        activeTab.set('create');
    };

    const scrollToAndSelectClassifier = (classifierId: string) => {
        scrollToClassifierId.set(classifierId);
        // Reset after a short delay to allow the scroll to complete
        setTimeout(() => {
            scrollToClassifierId.set(null);
        }, 100);
    };

    return {
        isDialogOpen,
        activeTab,
        scrollToClassifierId,
        openClassifiersMenu,
        closeClassifiersMenu,
        switchToManageTab,
        switchToCreateTab,
        scrollToAndSelectClassifier
    };
}
