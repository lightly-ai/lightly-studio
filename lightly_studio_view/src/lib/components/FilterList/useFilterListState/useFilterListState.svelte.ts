import { SvelteSet } from 'svelte/reactivity';
import { matchesSearch, type FilterListItem } from '../filterList.helpers';

// Rendering thousands of rows (e.g. a metadata field with a unique value per image) blocks
// the page for seconds, so long lists render in pages. Search still covers every item.
const PAGE_SIZE = 50;

interface UseFilterListStateParams {
    getItems: () => FilterListItem[];
    getShowSearch: () => boolean | undefined;
    getPaged: () => boolean;
}

/** Search and paging state of a FilterList. */
export function useFilterListState({
    getItems,
    getShowSearch,
    getPaged
}: UseFilterListStateParams) {
    let search = $state('');
    let shownCount = $state(PAGE_SIZE);
    // Rows past the page that the user toggled. They stay visible after being unticked,
    // so a misclick can be undone.
    const kept = new SvelteSet<string>();
    const isPinned = (item: FilterListItem) => item.selected || kept.has(item.id);

    const matching = $derived(getItems().filter((item) => matchesSearch(item, search)));
    // Selected and kept rows past the page stay visible, so an active filter is never hidden.
    const shown = $derived(
        getPaged()
            ? [...matching.slice(0, shownCount), ...matching.slice(shownCount).filter(isPinned)]
            : matching
    );

    return {
        get search() {
            return search;
        },
        setSearch(value: string) {
            search = value;
            shownCount = PAGE_SIZE;
            kept.clear();
        },
        keep(id: string) {
            kept.add(id);
        },
        /** Stays visible while a query is active, so the user can always clear it. */
        get searchVisible() {
            return (getShowSearch() ?? getItems().length > 5) || search.length > 0;
        },
        get matching() {
            return matching;
        },
        get shown() {
            return shown;
        },
        get nextPageCount() {
            return Math.min(PAGE_SIZE, matching.length - shown.length);
        },
        /** Reveals the next page of hidden rows, skipping rows past the page that are already shown. */
        showMore() {
            let revealed = 0;
            while (shownCount < matching.length && revealed < PAGE_SIZE) {
                if (!isPinned(matching[shownCount])) revealed++;
                shownCount++;
            }
        }
    };
}
