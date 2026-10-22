import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PluginCatalogRow from './PluginCatalogRow.svelte';

const plugin = {
    id: 'lightly_plugins_demo',
    name: 'Demo',
    description: 'A demo plugin',
    maintainer: 'lightly',
    tags: ['auto-labeling'],
    installed: false
};

const defaultProps = { plugin, installAllowed: true, onInstall: vi.fn() };

describe('PluginCatalogRow', () => {
    it('shows the plugin and installs it on click', async () => {
        const onInstall = vi.fn();
        render(PluginCatalogRow, { props: { ...defaultProps, onInstall } });

        expect(screen.getByText('Demo')).toBeInTheDocument();
        expect(screen.getByText('A demo plugin')).toBeInTheDocument();
        expect(screen.getByText('auto-labeling')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: /Install/ }));
        expect(onInstall).toHaveBeenCalledWith(plugin);
    });

    it('marks an installed plugin and offers no install', () => {
        render(PluginCatalogRow, {
            props: { ...defaultProps, plugin: { ...plugin, installed: true } }
        });

        expect(screen.getByText('Installed')).toBeInTheDocument();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('shows the progress of a running install', () => {
        const job = {
            job_id: 'job-1',
            plugin_id: plugin.id,
            status: 'running' as const,
            log: 'Resolved 3 packages\nDownloading numpy'
        };
        render(PluginCatalogRow, { props: { ...defaultProps, job } });

        expect(screen.getByRole('button', { name: /Installing/ })).toBeDisabled();
        expect(screen.getByText('Downloading numpy')).toBeInTheDocument();
    });

    it('shows the error and the log of a failed install, and offers a retry', () => {
        const job = {
            job_id: 'job-1',
            plugin_id: plugin.id,
            status: 'failed' as const,
            error_message: 'The installer exited with code 1.',
            log: 'error: No solution found'
        };
        render(PluginCatalogRow, { props: { ...defaultProps, job } });

        expect(screen.getByText('The installer exited with code 1.')).toBeInTheDocument();
        expect(screen.getByText('error: No solution found')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Retry/ })).toBeEnabled();
    });

    it('hides the install button when installs are not allowed', () => {
        render(PluginCatalogRow, { props: { ...defaultProps, installAllowed: false } });

        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});
