import hashlib,json,shutil,sys,tempfile,zipfile
from datetime import datetime
from pathlib import Path
ALLOW={'supplier_invoice_afi_upload.model.json','supplier_invoice_afi_upload.prompt.md','supplier_invoice_afi_upload.schema.json'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if len(sys.argv)!=2:raise SystemExit('Aufruf: python MODELLPATCH_ANWENDEN.py <Patch.zip>')
target=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
 w=Path(td)
 with zipfile.ZipFile(sys.argv[1]) as z:z.extractall(w)
 m=json.loads((w/'model_patch_manifest.json').read_text(encoding='utf-8'));files=m['files'];assert not(set(files)-ALLOW)
 for n,h in files.items():assert sha(w/n)==h,f'Prüfsumme falsch: {n}'
 backup=target/'model_patch_backups'/datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
 for n in files:
  if (target/n).exists():shutil.copy2(target/n,backup/n)
  shutil.copy2(w/n,target/n)
print('Modellpatch erfolgreich:',m['profile_version'])
