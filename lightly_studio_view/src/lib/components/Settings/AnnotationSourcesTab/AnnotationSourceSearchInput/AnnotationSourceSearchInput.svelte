<script lang="ts">
    import { AnnotationClassSearchInput } from '../../AnnotationClassesTab/AnnotationClassSearchInput';

    interface Props {
        value: string;
        onkeydown: (event: KeyboardEvent) => void;
    }

    let { value = $bindable(), onkeydown }: Props = $props();
</script>

<AnnotationClassSearchInput bind:value {onkeydown} label="Find or add an annotation source" />
