const itemCount = (count: number) => `${count} ${count === 1 ? 'item' : 'items'}`;

/** Toast after a tag add: counts only the items that did not have the tag. */
export function formatTagAddToast(tagName: string, changed: number, selected: number): string {
    if (changed === 0) return `All ${itemCount(selected)} already have '${tagName}'`;
    return `Added '${tagName}' to ${itemCount(changed)}`;
}

/** Toast after a tag remove: counts only the items that had the tag. */
export function formatTagRemoveToast(tagName: string, changed: number, selected: number): string {
    if (changed === 0) return `None of the ${itemCount(selected)} have '${tagName}'`;
    return `Removed '${tagName}' from ${itemCount(changed)}`;
}
