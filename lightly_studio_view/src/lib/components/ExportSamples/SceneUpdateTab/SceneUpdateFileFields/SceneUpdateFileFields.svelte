<script lang="ts">
    import { FormField } from '$lib/components';
    import { Input } from '$lib/components/ui/input';
    import { isValidSuffix } from '../sceneUpdateFileOptions';

    interface Props {
        /** The topic to write the SceneUpdate messages on. */
        topic: string;
        /** Inserted before the `.mcap` extension of each recording's file name. */
        suffix: string;
        onTopicChange: (topic: string) => void;
        onSuffixChange: (suffix: string) => void;
    }

    let { topic, suffix, onTopicChange, onSuffixChange }: Props = $props();
</script>

<FormField label="Topic" description="Use the same topic to add the annotations again.">
    <Input
        value={topic}
        oninput={(e) => onTopicChange(e.currentTarget.value)}
        data-testid="scene-update-topic-input"
    />
</FormField>
<FormField
    label="File Suffix"
    description={suffix
        ? `Each file is named after its recording with ${suffix}.mcap at the end.`
        : 'Each file has the same name as its recording.'}
>
    <Input
        value={suffix}
        oninput={(e) => onSuffixChange(e.currentTarget.value)}
        data-testid="scene-update-suffix-input"
    />
</FormField>
{#if !topic}
    <p class="text-sm text-destructive">Enter a topic.</p>
{/if}
{#if !isValidSuffix(suffix)}
    <p class="text-sm text-destructive">
        The suffix can only contain letters, digits, '_', '.' and '-'.
    </p>
{/if}
