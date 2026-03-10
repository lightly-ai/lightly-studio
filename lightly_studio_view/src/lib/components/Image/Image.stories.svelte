<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Image from './Image.svelte';

    const { Story } = defineMeta({
        title: 'Components/Image',
        component: Image,
        tags: ['autodocs'],
        argTypes: {
            src: { control: 'text' },
            className: { control: 'text' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        src: 'https://picsum.photos/200/200'
    }}
/>

<Story
    name="Custom Size"
    args={{
        src: 'https://picsum.photos/300/200',
        className: 'h-64 w-64'
    }}
/>

<Story name="Multiple Images" asChild>
    <div class="flex gap-4">
        <Image src="https://picsum.photos/200/200?random=1" className="h-40 w-40" />
        <Image src="https://picsum.photos/200/200?random=2" className="h-40 w-40" />
        <Image src="https://picsum.photos/200/200?random=3" className="h-40 w-40" />
    </div>
</Story>

<Story name="Different Aspect Ratios" asChild>
    <div class="flex flex-col gap-4">
        <Image src="https://picsum.photos/400/200" className="w-full max-w-md" />
        <Image src="https://picsum.photos/200/400" className="w-full max-w-md" />
        <Image src="https://picsum.photos/300/300" className="w-full max-w-md" />
    </div>
</Story>
