<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Alert from './index.svelte';

    const { Story } = defineMeta({
        title: 'Components/Alert',
        component: Alert,
        tags: ['autodocs'],
        argTypes: {
            title: { control: 'text' }
        }
    });
</script>

<Story name="Default" args={{ title: 'Error' }}>
    {#snippet children()}
        Something went wrong. Please try again.
    {/snippet}
</Story>

<Story name="Short Message" args={{ title: 'Attention' }}>
    {#snippet children()}
        Invalid input.
    {/snippet}
</Story>

<Story name="Long Message" args={{ title: 'Connection Error' }}>
    {#snippet children()}
        Unable to connect to the server. Please check your internet connection and try again. If the
        problem persists, contact support.
    {/snippet}
</Story>

<Story name="With List" args={{ title: 'Validation Errors' }}>
    {#snippet children()}
        <ul class="mt-2 list-inside list-disc">
            <li>Name is required</li>
            <li>Email format is invalid</li>
            <li>Password must be at least 8 characters</li>
        </ul>
    {/snippet}
</Story>
