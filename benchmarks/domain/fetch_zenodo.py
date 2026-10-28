# ruff: noqa: E401, E701, E702, I001
import json,sys,urllib.request,os
rid=sys.argv[1]; maxsize=int(sys.argv[2]) if len(sys.argv)>2 else 30_000_000
d=json.load(urllib.request.urlopen(f"https://zenodo.org/api/records/{rid}",timeout=30))
os.makedirs(rid,exist_ok=True)
json.dump({"title":d['metadata']['title'],"doi":d.get('doi'),"license":d['metadata'].get('license'),"creators":[c['name'] for c in d['metadata']['creators']],"description":d['metadata'].get('description','')[:3000],"related":d['metadata'].get('related_identifiers')},open(f"{rid}/meta.json","w"),indent=1,ensure_ascii=False)
for f in d['files']:
  if f['size']>maxsize: print('skip',f['key'],f['size']); continue
  p=f"{rid}/{f['key']}"
  if not os.path.exists(p): urllib.request.urlretrieve(f['links']['self'],p)
  print(rid,f['key'],f['size'])
