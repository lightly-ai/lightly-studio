import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';

interface Params {
    getChannels: () => ChannelSummaryView[];
    getResetKey: () => string;
}

export function useChannelSelection({ getChannels, getResetKey }: Params) {
    let selectedChannels = $state<number[] | null>(null);

    const channelIds = $derived(getChannels().map((channel) => channel.channel_id));
    const selectedChannelIds = $derived(selectedChannels ?? channelIds);
    const selectedChannelNames = $derived(
        getChannels()
            .filter((channel) => selectedChannelIds.includes(channel.channel_id))
            .map((channel) => channel.group_component_name)
    );

    const toggleChannel = (channelId: number) => {
        selectedChannels = selectedChannelIds.includes(channelId)
            ? selectedChannelIds.filter((id) => id !== channelId)
            : [...selectedChannelIds, channelId];
    };

    const setChannels = (channelIds: number[]) => {
        selectedChannels = channelIds;
    };

    $effect(() => {
        getResetKey();
        selectedChannels = null;
    });

    return {
        get selectedChannels() {
            return selectedChannels;
        },
        get selectedChannelIds() {
            return selectedChannelIds;
        },
        get selectedChannelNames() {
            return selectedChannelNames;
        },
        toggleChannel,
        setChannels
    };
}
