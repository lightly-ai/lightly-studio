#TODO: delete this after testing
import lightly_studio as ls

ls.connect(api_url='http://localhost:8100', token='<add_your_token_here>')
# ls.connect(api_url='http://100.87.208.47:8555/', token='<add_your_token_here>')
# ls.connect() # after setting env vars

ds = ls.ImageDataset.load("dataset_with_images")

[print(sample.file_name) for sample in ds.slice(limit=3)]
