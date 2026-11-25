/** A name per collection, for example the class or the source that new annotations get. */
type NamePerCollection = Record<string, string>;

/** Returns `names` with `oldName` of the collection changed to `newName`. */
export const renameForCollection = (
    names: NamePerCollection,
    collectionId: string,
    oldName: string,
    newName: string
): NamePerCollection =>
    names[collectionId] === oldName ? { ...names, [collectionId]: newName } : names;

/** Returns `names` without the entry of the collection when it is `name`. */
export const removeForCollection = (
    names: NamePerCollection,
    collectionId: string,
    name: string
): NamePerCollection => {
    if (names[collectionId] !== name) return names;
    const next = { ...names };
    delete next[collectionId];
    return next;
};
