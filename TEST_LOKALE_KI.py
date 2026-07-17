import argparse,json,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--download-model',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent;profile=json.loads((root/'supplier_invoice_afi_upload.model.json').read_text(encoding='utf-8-sig'))
from foundry_local_sdk import Configuration,FoundryLocalManager
data=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'FiBuMate'/'FoundryLocal';data.mkdir(parents=True,exist_ok=True);FoundryLocalManager.initialize(Configuration(app_name='FiBuMate',app_data_dir=str(data),model_cache_dir=str(data/'models'),logs_dir=str(data/'logs')));m=FoundryLocalManager.instance;print('Foundry Local SDK: OK')
try:m.download_and_register_eps(progress_callback=lambda n,p:print(f'EP {n}: {p:.0f}%',end='\r'))
except Exception as e:print('\nHardwarehinweis:',e)
model=m.catalog.get_model(profile['model_alias']);assert model is not None,'Modell fehlt im Katalog';print('\nModell:',profile['model_alias'],'| lokal:',bool(model.is_cached))
if a.download_model and not model.is_cached:model.download(progress_callback=lambda p:print(f'Modell: {p:.0f}%',end='\r'))
if a.download_model or model.is_cached:
 model.load();client=model.get_chat_client();client.settings.max_tokens=50;r=client.complete_chat([{'role':'user','content':'Antworte exakt mit FIBU_MATE_OK'}]);print('\nAntwort:',r.choices[0].message.content);model.unload()
print('TEST_ABGESCHLOSSEN')
