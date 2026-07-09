import { formatFloat2 } from './formatFloat';

export const formatConfidence = (confidence?: number | null): string | null => {
    if (confidence == null) {
        return null;
    }

    return formatFloat2(confidence);
};
