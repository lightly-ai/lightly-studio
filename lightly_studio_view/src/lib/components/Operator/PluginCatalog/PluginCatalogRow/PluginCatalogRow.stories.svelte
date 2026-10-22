<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import PluginCatalogRow from './PluginCatalogRow.svelte';

    const plugin = {
        id: 'lightly_plugins_sam3_segmentation',
        name: 'SAM3',
        description:
            'Segments all instances matching a table of text prompts in a single image or the current image view',
        maintainer: 'lightly',
        installed: false
    };

    const { Story } = defineMeta({
        title: 'Components/Operator/PluginCatalogRow',
        component: PluginCatalogRow,
        tags: ['autodocs'],
        args: { plugin, installAllowed: true, onInstall: () => {} }
    });
</script>

<Story name="Not installed" />
<Story name="Installed" args={{ plugin: { ...plugin, installed: true } }} />
<Story
    name="Installing"
    args={{
        job: {
            job_id: 'job-1',
            plugin_id: plugin.id,
            status: 'running',
            log: 'Downloading torch (70.1MiB)'
        }
    }}
/>
<Story
    name="Failed"
    args={{
        job: {
            job_id: 'job-1',
            plugin_id: plugin.id,
            status: 'failed',
            error_message: 'The installer exited with code 1.',
            log: 'error: Because lightly-studio==1.1.3 ... no solution found'
        }
    }}
/>
<Story name="Install not allowed" args={{ installAllowed: false }} />
