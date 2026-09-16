/**
 * Test id of the "Assign tag to selection" field in the sidebar's Tags group.
 *
 * The sidebar's selection card has no field of its own — its Tag button hands focus to this
 * one, so the tag flow stays in a single place instead of being duplicated per entry point.
 */
export const TAG_ASSIGN_INPUT_TEST_ID = 'tag-assign-input';

/** Reveals the tag field and focuses it. No-op when the Tags group is not rendered. */
export function focusTagAssignInput(): void {
    const input = document.querySelector<HTMLInputElement>(
        `[data-testid="${TAG_ASSIGN_INPUT_TEST_ID}"]`
    );
    if (!input) return;
    input.scrollIntoView({ block: 'nearest' });
    input.focus();
}
