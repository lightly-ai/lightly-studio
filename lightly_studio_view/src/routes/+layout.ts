import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
// dummy change

// Initialize the global storage hook
const globalStorage = useGlobalStorage();

export const ssr = false;

export const load = async () => {
    return {
        globalStorage
    };
};
