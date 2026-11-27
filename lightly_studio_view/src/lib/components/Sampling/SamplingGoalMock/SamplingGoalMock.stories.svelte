<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import SamplingGoalMock from './SamplingGoalMock.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/SamplingGoalMock',
        component: SamplingGoalMock,
        parameters: { layout: 'fullscreen' }
    });
</script>

<Story name="With unavailable choices" args={{ showUnavailable: true }}>
    {#snippet children({ args })}
        <div class="p-6"><SamplingGoalMock {...args} /></div>
    {/snippet}
</Story>

<Story name="All choices available" args={{ showUnavailable: false }}>
    {#snippet children({ args })}
        <div class="p-6"><SamplingGoalMock {...args} /></div>
    {/snippet}
</Story>
