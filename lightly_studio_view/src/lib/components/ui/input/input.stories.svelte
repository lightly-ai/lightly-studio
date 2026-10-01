<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Input from './input.svelte';

    const { Story } = defineMeta({
        title: 'Components/Primitives/Input',
        component: Input,
        tags: ['autodocs'],
        parameters: {
            layout: 'centered'
        },
        argTypes: {
            isPending: {
                description:
                    'When true, disables the input and shows an indeterminate linear progress bar at the bottom, consistent with Button.isPending.',
                control: 'boolean'
            },
            disabled: {
                description: 'Disables the input without showing a progress indicator.',
                control: 'boolean'
            },
            placeholder: {
                description: 'Placeholder text shown when the input is empty.',
                control: 'text'
            },
            value: {
                description: 'Current value of the input.',
                control: 'text'
            },
            class: {
                description: 'Additional CSS classes applied to the input element.',
                control: 'text'
            }
        }
    });
</script>

<script>
    let tagValue = $state('');
    let tagIsPending = $state(false);

    function assignTag() {
        if (!tagValue || tagIsPending) return;
        tagIsPending = true;
        setTimeout(() => {
            tagIsPending = false;
        }, 2000);
    }
</script>

<Story name="Default" args={{ placeholder: 'Type something…' }} />

<Story name="WithValue" args={{ value: 'frontend-bug' }} />

<Story name="Pending" args={{ isPending: true, placeholder: 'Assigning tag…' }} />

<Story name="PendingWithValue" args={{ isPending: true, value: 'frontend-bug' }} />

<Story name="Disabled" args={{ disabled: true, value: 'read-only-value' }} />

<Story name="TagAssignment">
    {#snippet template()}
        <div class="flex w-72 gap-2">
            <Input
                bind:value={tagValue}
                isPending={tagIsPending}
                placeholder="Enter tag name…"
                class="flex-1"
            />
            <button
                class="rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-50"
                disabled={tagIsPending || !tagValue}
                onclick={assignTag}
            >
                Assign
            </button>
        </div>
    {/snippet}
</Story>
