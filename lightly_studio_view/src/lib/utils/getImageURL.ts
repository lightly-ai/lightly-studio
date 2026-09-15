import { PUBLIC_SAMPLES_URL } from '$env/static/public';
import { withProxyMediaMode } from './mediaRecovery';

interface GetImageURLOptions {
    mode?: 'proxy';
}

export const getImageURL = (imageID: string, options: GetImageURLOptions = {}): string => {
    const url = `${PUBLIC_SAMPLES_URL}/sample/${imageID}`;
    return options.mode === 'proxy' ? withProxyMediaMode(url) : url;
};
