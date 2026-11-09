import { matchesSearch, type FilterListItem } from './filterList.helpers';

// Rendering thousands of rows (e.g. a metadata field with a unique value per image) blocks
// the page for seconds, so long lists render in pages. Search still covers every item.
const PAGE_SIZE = 50;

interface UseFilterListStateParams {
    getItems: () => FilterListItem[];
    getShowSearch: () => boolean | undefined;
}

/** Search and paging state of a FilterList. */
export function useFilterListState({ getItems, getShowSearch }: UseFilterListStateParams) {
    let search = $state('');
    let shownCount = $state(PAGE_SIZE);

    const visible = $derived(getItems().filter((item) => matchesSearch(item, search)));
    const shown = $derived(visible.slice(0, shownCount));

    return {
        get search() {
            return search;
        },
        setSearch(value: string) {
            search = value;
            shownCount = PAGE_SIZE;
        },
        /** Stays visible while a query is active, so the user can always clear it. */
        get searchVisible() {
            return (getShowSearch() ?? getItems().length > 5) || search.length > 0;
        },
        get visible() {
            return visible;
        },
        get shown() {
            return shown;
        },
        get nextPageCount() {
            return Math.min(PAGE_SIZE, visible.length - shown.length);
        },
        showMore() {
            shownCount += PAGE_SIZE;
        }
    };
}
