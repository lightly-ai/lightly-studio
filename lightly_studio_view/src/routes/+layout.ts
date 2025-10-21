import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

// Initialize the global storage hook
const globalStorage = useGlobalStorage();

export const load = async () => {
    return {
        globalStorage
    };
};
