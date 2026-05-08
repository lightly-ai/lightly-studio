import * as monaco from 'monaco-editor';
import { URI } from 'langium';
import type { LightlyQueryServicesBundle } from '../../language/lightly-query-module';

/** Rebuild the Langium document from Monaco text so providers see fresh content. */
export async function syncLangiumDocument(
    model: monaco.editor.ITextModel,
    services: LightlyQueryServicesBundle
) {
    const {
        shared: {
            workspace: { LangiumDocuments: documents, DocumentBuilder: builder }
        }
    } = services;

    const uri = URI.parse(model.uri.toString());
    documents.deleteDocument(uri);
    const doc = documents.createDocument(uri, model.getValue());
    await builder.build([doc], { validation: false });
    return doc;
}
