/**
 * Constructs a URL with optional query parameters
 * @param basePath - The base path without query string
 * @param params - Optional query parameters as key-value pairs
 * @returns URL with query string if params are provided, otherwise just basePath
 */
export function getURL(
    basePath: string,
    params?: Record<string, string | number | boolean | undefined>
): string {
    if (!params) {
        return basePath;
    }

    const urlParams = new URLSearchParams();

    for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null && value !== '') {
            urlParams.append(key, String(value));
        }
    }

    const query = urlParams.toString();
    return query ? `${basePath}?${query}` : basePath;
}
