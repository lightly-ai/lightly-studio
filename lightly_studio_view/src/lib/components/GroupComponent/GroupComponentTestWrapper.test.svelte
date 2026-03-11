<script lang="ts">
    import GroupComponent from './GroupComponent.svelte';

    let {
        src,
        type,
        title
    }: {
        src: string;
        title: string;
        type: 'image' | 'video';
    } = $props();
</script>

<GroupComponent {src} {type} {title} />
