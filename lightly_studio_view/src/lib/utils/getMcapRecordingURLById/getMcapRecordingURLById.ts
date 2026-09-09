import { PUBLIC_MCAP_MEDIA_URL } from '$env/static/public';

/**
 * URL that serves the recording an MCAP sample points into, as byte ranges.
 *
 * The browser reads point-cloud frames straight from the indexed recording, so this is
 * the recording itself rather than a decoded frame.
 */
export const getMcapRecordingURLById = (sampleId: string): string =>
    `${PUBLIC_MCAP_MEDIA_URL}/${sampleId}`;
