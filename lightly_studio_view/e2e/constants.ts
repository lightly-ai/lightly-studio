import type { CDPSession } from '@playwright/test';

type NetworkConditions = Parameters<CDPSession['send']>[1] & { connectionType?: string };

export const NETWORK_PRESETS = {
    Fast4G: {
        offline: false,
        downloadThroughput: (4 * 1024 * 1024) / 8, // 4 Mbps
        uploadThroughput: (3 * 1024 * 1024) / 8, // 3 Mbps
        latency: 20, // 20ms
        connectionType: 'cellular4g'
    }
} as const satisfies Record<string, NetworkConditions>;

export type NetworkPreset = keyof typeof NETWORK_PRESETS;
