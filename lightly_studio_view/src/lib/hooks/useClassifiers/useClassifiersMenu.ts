import { writable, type Readable } from 'svelte/store';

interface UseClassifiersMenuReturn {
    isDropdownOpen: Readable<boolean>;
    activeTab: Readable<string>;
    scrollToClassifierId: Readable<string | null>;
    openClassifiersMenu: () => void;
    closeClassifiersMenu: () => void;
    switchToManageTab: () => void;
    switchToCreateTab: () => void;
    scrollToAndSelectClassifier: (classifierId: string) => void;
}

const isDropdownOpen = writable<boolean>(false);
const activeTab = writable<string>('create');
const scrollToClassifierId = writable<string | null>(null);

export function useClassifiersMenu(): UseClassifiersMenuReturn {
    const openClassifiersMenu = () => {
        isDropdownOpen.set(true);
    };

    const closeClassifiersMenu = () => {
        isDropdownOpen.set(false);
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
        isDropdownOpen,
        activeTab,
        scrollToClassifierId,
        openClassifiersMenu,
        closeClassifiersMenu,
        switchToManageTab,
        switchToCreateTab,
        scrollToAndSelectClassifier
    };
}
