<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ConfusionMatrix from './ConfusionMatrix.svelte';

    const { Story } = defineMeta({
        title: 'Components/ConfusionMatrix',
        component: ConfusionMatrix,
        tags: ['autodocs']
    });
</script>

<script lang="ts">
    import { empty, large20Classes, medium8Classes, singleClass, small3Classes } from './fixtures';
</script>

<Story name="Small (3 classes)" args={{ matrix: small3Classes }} />

<Story name="Medium (8 classes)" args={{ matrix: medium8Classes }} />

<Story name="Large (20 classes)" args={{ matrix: large20Classes }} />

<Story name="Empty" args={{ matrix: empty }} />

<Story name="Single class" args={{ matrix: singleClass }} />

<Story name="With legend" args={{ matrix: medium8Classes, showLegend: true }} />
