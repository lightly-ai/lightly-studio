/** Which hover buttons a tag row shows: + when not all selected items have the tag, × when any do. */
export function tagRowActions(
    count: number,
    total: number
): { canAdd: boolean; canRemove: boolean } {
    return { canAdd: count < total, canRemove: count > 0 };
}
