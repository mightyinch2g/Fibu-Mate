import hashlib,json,zipfile
from pathlib import Path
r=Path(__file__).resolve().parent;files=['supplier_invoice_afi_upload.model.json','supplier_invoice_afi_upload.prompt.md','supplier_invoice_afi_upload.schema.json'];p=json.loads((r/files[0]).read_text(encoding='utf-8-sig'));sha=lambda x:hashlib.sha256((r/x).read_bytes()).hexdigest();m={'patch_format':1,'profile_version':p['profile_version'],'model_alias':p['model_alias'],'files':{x:sha(x) for x in files}};out=r/f"FiBuMate_Modellpatch_{p['profile_version']}.zip"
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for x in files:z.write(r/x,x)
 z.writestr('model_patch_manifest.json',json.dumps(m,indent=2))
print(out)
