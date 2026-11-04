import { derived, type Readable } from 'svelte/store';
import { useWebStorage } from '../useWebStorage/useWebStorage';

const defaultSources = useWebStorage<Record<string, string>>(
    'localStorage',
    'lightlyStudio_default_annotation_source',
    {}
);

/** The annotation source seeded when entering edit mode, per collection. */
export function useDefaultSource(): {
    defaultSources: Readable<Record<string, string>>;
    /** At most one default per collection; null removes it. */
    setDefaultSource: (collectionId: string, sourceName: string | null) => void;
    renameDefaultSource: (collectionId: string, oldName: string, newName: string) => void;
} {
    return {
        defaultSources: derived(defaultSources, (value) => value),
        setDefaultSource: (collectionId, sourceName) => {
            defaultSources.update((value) => {
                const next = { ...value };
                if (sourceName === null) delete next[collectionId];
                else next[collectionId] = sourceName;
                return next;
            });
        },
        renameDefaultSource: (collectionId, oldName, newName) => {
            defaultSources.update((value) =>
                value[collectionId] === oldName ? { ...value, [collectionId]: newName } : value
            );
        }
    };
}
