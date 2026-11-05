// Used when neither the selected class nor a hint gives a class name.
const FALLBACK_CLASS_NAME = 'object';

// A selected class wins as is, even with a blank name. A blank hint falls back.
export const pickClassName = ({
    selected,
    hint
}: {
    selected: string | null | undefined;
    hint: string | null | undefined;
}): string => selected ?? (hint?.trim() || FALLBACK_CLASS_NAME);
