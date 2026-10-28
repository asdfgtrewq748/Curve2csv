# Provenance script (not run in CI). Requires pandas+openpyxl and the Zenodo files
# downloaded by zdl.py-style fetch into the working dir (see sources.json source_url).
# Run from that working dir: python prep_sources.py  -> writes sources/<slug>.csv.
"""Extract single published curves from downloaded open datasets into curves/<slug>.csv (x,y)."""
import json, glob
import numpy as np, pandas as pd
Z="https://doi.org/10.5281/zenodo."
out={}
def put(slug, x, y, rid, lic, fileref, xl, yl, notes, xscale="linear", yscale="linear", kind=""):
    x=np.asarray(x,float); y=np.asarray(y,float)
    m=np.isfinite(x)&np.isfinite(y); x=x[m]; y=y[m]
    out[slug]=dict(slug=slug,x=x.tolist(),y=y.tolist(),zenodo=rid,source_url=Z+str(rid),license=lic,
                   source_file=fileref,x_label=xl,y_label=yl,notes=notes,x_scale=xscale,y_scale=yscale,kind=kind,
                   title=json.load(open(f"{rid}/meta.json"))["title"])
# 4072158 anchor surrounding rock (PLOS ONE), CC0
a=pd.read_excel('4072158/Data.xlsx',sheet_name='strain-stress',header=None)
for slug,c,name in [("anchor-coal1",0,"Coal 1"),("anchor-sandymudstone1",4,"Sandy mudstone 1"),("anchor-sandstone1",8,"Sandstone 1"),("anchor-coal2",2,"Coal 2")]:
    put(slug,a.iloc[1:,c],a.iloc[1:,c+1],4072158,"CC0-1.0",f"Data.xlsx/strain-stress/{name}","Strain (%)","Stress (MPa)",f"sheet strain-stress, columns '{name}'","linear","linear","stress-strain")
# 4959298 floor heave longwall gateroads (CC0)
for sheet in ("shales","sandstones"):
    d=pd.read_excel('4959298/Data.xlsx',sheet_name=sheet,header=None)
    for k,cp in enumerate([0,5,15,25]):
        c=5*k
        put(f"gateroad-{sheet[:-1]}-{cp}mpa",d.iloc[2:,c],d.iloc[2:,c+1],4959298,"CC0-1.0",f"Data.xlsx/{sheet}/confining {cp} MPa","Axial strain (mm/mm)","Axial stress (MPa)",f"{sheet}, confining pressure {cp} MPa, cols axial strain/axial stress","linear","linear","triaxial stress-strain")
# 3929410 longwall gob compaction
for t in ("A","B"):
    d=pd.read_excel('3929410/Raw data of Test A and Test B_force-displacement.xlsx',sheet_name=f"Test {t}")
    put(f"gob-compaction-test{t.lower()}",d.iloc[:,1],d.iloc[:,0],3929410,"CC-BY-4.0",f"Raw data .../Test {t}","Displacement (mm)","Force (kN)","cols Force kN, Displacement mm","linear","linear","force-displacement")
# 17059631 red sandstone triaxial (MTS)
for s in (1,2,3,4):
    rows=[]
    for line in open(f'17059631/specimen{s}.dat',encoding='latin1'):
        p=line.strip().split('\t')
        if len(p)==6:
            try: rows.append([float(v) for v in p])
            except ValueError: pass
    d=pd.DataFrame(rows)
    put(f"redsandstone-triaxial-s{s}",d.iloc[:,2],d.iloc[:,4]/1000.0,17059631,"CC-BY-4.0",f"specimen{s}.dat","Axial extension (mm)","Axial force (kN)","cols Axial Ext (mm), Force N/1000","linear","linear","force-extension")
# 4991755 coal pillar stress Fig.7 (CC0) - published figure data
d=pd.read_excel('4991755/Data.xlsx',header=None)
rows=d.iloc[3:32,:]
for c,lab in [(1,"a"),(2,"b"),(3,"c")]:
    xx=pd.to_numeric(rows.iloc[:,0],errors='coerce'); yy=pd.to_numeric(rows.iloc[:,c],errors='coerce')
    # stop at first non-numeric row block (Fig.7 table ends)
    put(f"roofcut-pillar-fig7{lab}",xx,yy,4991755,"CC0-1.0",f"Data.xlsx Fig.7({lab})","Horizontal position (m)","Vertical stress (MPa)","published data of Fig.7; rows 4.. until blank","linear","linear","stress profile")
# 4995955 Fig.12 rows
d=pd.read_excel('4995955/Data.xlsx',header=None)
def rowvals(r): return pd.to_numeric(d.iloc[r,3:],errors='coerce').values
for name,(rx,ry),xl,yl in [("portal-fig12a-unit",(0,1),"Horizontal position (m)","Vertical stress (MPa)"),("portal-fig12a-portal",(2,3),"Horizontal position (m)","Vertical stress (MPa)")]:
    put(name,rowvals(rx),rowvals(ry),4995955,"CC0-1.0",f"Data.xlsx Fig.12(a) rows {rx},{ry}",xl,yl,"published Fig.12(a) data","linear","linear","stress profile")
# 4942609 UCT kaiser
for n in (1,2,3,4,5,6):
    d=pd.read_csv(f'4942609/UCT and AE test date/#{n}.csv',header=None,skiprows=7,usecols=[0,1,2,3,4],low_memory=False)
    put(f"kaiser-uct{n}",d.iloc[:,0],d.iloc[:,4],4942609,"CC0-1.0",f"UCT and AE test date/#{n}.csv","Time (s)","Stress (MPa)","cols time(s), stress(MPa)","linear","linear","stress-time")
# 10598216 limestone UCS
for f in sorted(glob.glob('10598216/Uniaxial compression/*U_*.txt')):
    if f.endswith('_AE.txt'): continue
    d=pd.read_csv(f,sep=r'\s+',skiprows=1,header=None)
    base=f.split('/')[-1][:-4]
    put(f"limestone-ucs-{base.lower().replace('_','-')}",d.iloc[:,1]*100,d.iloc[:,0],10598216,"CC-BY-4.0",f"Uniaxial compression/{base}.txt","Axial strain (%)","Axial stress (MPa)","col2 strain*100, col1 stress","linear","linear","stress-strain")
for f in sorted(glob.glob('10598216/KIc/*.txt')):
    d=pd.read_csv(f,sep=r'\s+',header=None,comment='#')
    d=d.apply(pd.to_numeric,errors='coerce').dropna()
    base=f.split('/')[-1][:-4]
    put(f"limestone-kic-{base.lower().replace('_','-')}",d.iloc[:,0],d.iloc[:,1],10598216,"CC-BY-4.0",f"KIc/{base}.txt","Axial displacement (mm)","K$_I$ (MPa m$^{1/2}$)","col1 disp, col2 KI","linear","linear","KI-displacement")
# 17743968 crystalline rock uniaxial
d=pd.read_excel('17743968/experimantal data_uniaxial.xlsx',header=None).iloc[6:,:]
put("granite-uniaxial-axial",pd.to_numeric(d.iloc[:,5],errors='coerce'),pd.to_numeric(d.iloc[:,2],errors='coerce'),17743968,"CC-BY-4.0","experimantal data_uniaxial.xlsx cols axial strain1/stress","Axial strain (%)","Stress (MPa)","col F (S04 strain gauge 1, %) vs col C stress","linear","linear","stress-strain")
# 23666827 clay creep: settlement vs elapsed time (log)
st=pd.read_csv('23666827/stages.csv')
for sid in ["C4K_s1","TCB7B_s2","NC1B_s1"]:
    r=st[st.stage_id==sid].iloc[0]
    d=pd.read_csv(f'23666827/stage_data/{sid}.csv')
    t=pd.to_datetime(d.iloc[:,0],format="%d/%m/%y %H:%M:%S",errors='coerce')
    if t.isna().mean()>0.5: t=pd.to_datetime(d.iloc[:,0],errors='coerce')
    t0=pd.Timestamp(r.t0_load)
    el=(t-t0).dt.total_seconds()/60.0
    s=d.iloc[:,1].astype(float)
    s=s-s.iloc[0]
    m=el>0
    put(f"clay-creep-{sid.lower().replace('_','-')}",el[m],s[m].abs(),23666827,"CC-BY-4.0",f"stage_data/{sid}.csv",
        "Elapsed time (min)","Settlement (mm)",f"stage {sid} sigma_v={r.sigma_v_kPa} kPa; time since t0_load; settlement=|dial-dial_first_row|","log10","linear","settlement-time")
json.dump(out,open('curves/all.json','w'))
for k,v in out.items(): print(k,len(v["x"])) if not v["x"] else print(k,len(v['x']),'x',round(min(v['x']),4),round(max(v['x']),4),'y',round(min(v['y']),4),round(max(v['y']),4))

# Cu oedometer control specimen (23356064): void ratio vs applied pressure
d=pd.read_excel('23356064/Cu_oedometer_raw.xlsx',sheet_name='Raw Measurements',header=1)
c=d[d['Specimen ID']=='Control']
put("oedometer-cu-control",c['Applied Pressure (kPa)'],c['Void Ratio (e)'],23356064,"CC-BY-4.0","Cu_oedometer_raw.xlsx/Raw Measurements/Control",
    "Vertical stress (kPa)","Void ratio, e","Control specimen, 6 load stages","log10","linear","e-log p")
json.dump(out,open('curves/all.json','w'))

SELECT=["anchor-coal1","anchor-sandymudstone1","anchor-sandstone1","gateroad-shale-0mpa","gateroad-shale-15mpa",
"gateroad-sandstone-0mpa","gateroad-sandstone-15mpa","gob-compaction-testa","gob-compaction-testb",
"roofcut-pillar-fig7a","roofcut-pillar-fig7b","roofcut-pillar-fig7c","kaiser-uct1","kaiser-uct3","kaiser-uct5",
"limestone-ucs-in1u-dry","limestone-ucs-l1u-dry","limestone-ucs-s1u-sat","limestone-ucs-t2u-sat","limestone-ucs-st1u-sat",
"clay-creep-c4k-s1","clay-creep-tcb7b-s2","clay-creep-nc1b-s1","oedometer-cu-control"]
MAXPTS=300
def curate(v):
    x=np.asarray(v['x']); y=np.asarray(v['y'])
    keep=[0]
    for i in range(1,len(x)):
        if x[i]>x[keep[-1]]: keep.append(i)
    x=x[keep]; y=y[keep]
    if len(x)>MAXPTS:
        xs=np.log10(x) if v['x_scale']=='log10' else x
        nx=(xs-xs.min())/(xs.max()-xs.min()); ny=(y-y.min())/(y.max()-y.min())
        s=np.concatenate([[0],np.cumsum(np.hypot(np.diff(nx),np.diff(ny)))])
        targets=np.linspace(0,s[-1],MAXPTS)
        idx=np.unique(np.concatenate([[0,len(x)-1],np.searchsorted(s,targets).clip(0,len(x)-1)]))
        x=x[idx]; y=y[idx]
    return x,y,len(v['x'])
import os
dst=os.environ.get('DOMAIN_SOURCES','sources'); os.makedirs(dst,exist_ok=True)
meta={}
for k in SELECT:
    v=out[k]; x,y,nraw=curate(v)
    pd.DataFrame({'x':x,'y':y}).to_csv(f'{dst}/{k}.csv',index=False,float_format='%.8g')
    meta[k]={kk:v[kk] for kk in v if kk not in('x','y')}; meta[k].update(n_raw=nraw,n_curated=len(x))
    print(k,nraw,'->',len(x))
LEGEND={"anchor-coal1": "Coal 1", "anchor-sandymudstone1": "Sandy mudstone 1", "anchor-sandstone1": "Sandstone 1", "gateroad-shale-0mpa": "Shale, σ3 = 0 MPa", "gateroad-shale-15mpa": "Shale, σ3 = 15 MPa", "gateroad-sandstone-0mpa": "Sandstone, σ3 = 0 MPa", "gateroad-sandstone-15mpa": "Sandstone, σ3 = 15 MPa", "gob-compaction-testa": "Test A", "gob-compaction-testb": "Test B", "roofcut-pillar-fig7a": "After excavation", "roofcut-pillar-fig7b": "Without roof cutting", "roofcut-pillar-fig7c": "With roof cutting", "kaiser-uct1": "Specimen #1", "kaiser-uct3": "Specimen #3", "kaiser-uct5": "Specimen #5", "limestone-ucs-in1u-dry": "Indiana, dry", "limestone-ucs-l1u-dry": "Leitha, dry", "limestone-ucs-s1u-sat": "Solnhofen, sat.", "limestone-ucs-t2u-sat": "Tavel, sat.", "limestone-ucs-st1u-sat": "St Maximin, sat.", "clay-creep-c4k-s1": "C4K, stage 1", "clay-creep-tcb7b-s2": "TCB7B, stage 2", "clay-creep-nc1b-s1": "NC1B, stage 1", "oedometer-cu-control": "Control"}
for k in meta: meta[k]['legend']=LEGEND[k]
json.dump(meta,open(f'{dst}/sources.json','w'),indent=1,ensure_ascii=False)
