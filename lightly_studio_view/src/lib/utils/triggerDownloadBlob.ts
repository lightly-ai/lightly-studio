export const triggerDownloadBlob = (fileName: string, blob: Blob): void => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    link.remove(); // you need to remove that elelment which is created before.

    // remove from memory
    window.URL.revokeObjectURL(url);
};
