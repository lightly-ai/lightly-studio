import { get, writable } from 'svelte/store';
import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import {
    getPluginInstallJob,
    installPlugin,
    InstallJobStatus,
    type CatalogPluginView,
    type InstallJob
} from '$lib/api/lightly_studio_local';
import {
    getOperatorsQueryKey,
    getPluginCatalogQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

export const POLL_INTERVAL_MS = 1000;

/** The last install job of each plugin, keyed by the plugin ID. Kept when the dialog closes. */
const jobs = writable<Record<string, InstallJob>>({});

type Plugin = Pick<CatalogPluginView, 'id' | 'name'>;

/** Installs catalog plugins on the server and polls each install until it ends. */
export function usePluginInstall() {
    const client = useQueryClient();

    const setJob = (job: InstallJob) => jobs.update((all) => ({ ...all, [job.plugin_id]: job }));

    const failLocally = (plugin: Plugin, message: string) => {
        setJob({
            job_id: '',
            plugin_id: plugin.id,
            status: InstallJobStatus.FAILED,
            error_message: message
        });
        toast.error(`Could not install ${plugin.name}`, { description: message });
    };

    const finish = (plugin: Plugin, job: InstallJob) => {
        client.invalidateQueries({ queryKey: getOperatorsQueryKey() });
        client.invalidateQueries({ queryKey: getPluginCatalogQueryKey() });
        if (job.status === InstallJobStatus.FAILED) {
            toast.error(`Could not install ${plugin.name}`, { description: job.error_message });
        } else if (job.error_message) {
            toast.warning(`${plugin.name} is installed`, { description: job.error_message });
        } else if (job.restart_recommended) {
            toast.success(`${plugin.name} is ready`, {
                description:
                    'The install updated packages in use. Restart LightlyStudio if the plugin fails.'
            });
        } else {
            toast.success(`${plugin.name} is ready`, {
                description: 'Find it in the Installed tab.'
            });
        }
    };

    const poll = async (plugin: Plugin, jobId: string) => {
        for (;;) {
            await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
            const { data, error } = await getPluginInstallJob({ path: { job_id: jobId } });
            if (error || !data) {
                failLocally(plugin, 'Lost the connection to the install job.');
                return;
            }
            setJob(data);
            if (
                data.status === InstallJobStatus.SUCCEEDED ||
                data.status === InstallJobStatus.FAILED
            ) {
                finish(plugin, data);
                return;
            }
        }
    };

    const install = async (plugin: Plugin) => {
        if (isInstalling(get(jobs)[plugin.id])) return;
        // Show the spinner at once. The server answers with the real job.
        setJob({ job_id: '', plugin_id: plugin.id, status: InstallJobStatus.QUEUED });
        const { data, error } = await installPlugin({ path: { plugin_id: plugin.id } });
        if (error || !data) {
            failLocally(
                plugin,
                (error as { error?: string } | undefined)?.error ??
                    'The server refused the install.'
            );
            return;
        }
        setJob(data);
        await poll(plugin, data.job_id);
    };

    return { jobs, install };
}

export const isInstalling = (job: InstallJob | undefined): boolean =>
    job?.status === InstallJobStatus.QUEUED || job?.status === InstallJobStatus.RUNNING;
