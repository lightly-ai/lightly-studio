const locale = 'en-US';

export const formatInteger = (num: number): string => {
    return new Intl.NumberFormat(locale, {}).format(num).toString();
};
export const formatFloat = (num: number, maxDigits = 3, minDigits = 0): string => {
    return new Intl.NumberFormat(locale, {
        maximumFractionDigits: maxDigits,
        minimumFractionDigits: minDigits
    })
        .format(num)
        .toString();
};
export const formatFloat2 = (num: number): string => {
    return formatFloat(num, 2);
};

/**
 * Format a metadata value for display
 * @param value - The metadata value to format
 * @returns Formatted string representation of the value
 */
export const formatMetadataValue = (value: unknown): string => {
    if (value === null || value === undefined) {
        return 'null';
    }

    if (typeof value === 'string') {
        return value;
    }

    if (typeof value === 'number') {
        if (Number.isInteger(value)) {
            return formatInteger(value);
        } else {
            return formatFloat(value);
        }
    }

    if (typeof value === 'boolean') {
        return value ? 'true' : 'false';
    }

    if (Array.isArray(value)) {
        if (value.length === 0) {
            return '[]';
        }
        if (value.length <= 3 && value.every((item) => typeof item !== 'object' || item === null)) {
            return `[${value.map((item) => formatMetadataValue(item)).join(', ')}]`;
        } else {
            const items = value.map((item) => formatMetadataValue(item)).join(', ');
            return `[${items}]`;
        }
    }

    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        const obj = value as Record<string, unknown>;
        const keys = Object.keys(obj);
        if (keys.length === 0) {
            return '{}';
        }

        // For simple objects with primitive values, show on one line
        if (
            keys.length <= 3 &&
            keys.every((key) => {
                const val = obj[key];
                return typeof val !== 'object' || val === null || Array.isArray(val);
            })
        ) {
            const pairs = keys.map((key) => `${key}: ${formatMetadataValue(obj[key])}`).join(', ');
            return `{${pairs}}`;
        }

        // For complex objects, format with line breaks but compact
        const pairs = keys
            .map((key) => {
                const formattedValue = formatMetadataValue(obj[key]);
                return `${key}: ${formattedValue}`;
            })
            .join('\n');

        return `{\n${pairs}\n}`;
    }

    return String(value);
};
