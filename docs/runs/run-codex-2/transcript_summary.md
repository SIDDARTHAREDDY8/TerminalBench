# codex trial 2 — command and message summary

## message
I’ll inspect the recording metadata, calibration, and available ROS/point-cloud tooling first. Then I’ll reconstruct the trajectory, validate scan consistency and timing, segment the aircraft from the apron/background, and export both files with geometric checks.

## cmd 1 (exit 0)
```
"pwd && rg --files -g 'AGENTS.md' -g '"'!proc'"' -g '"'!sys'"' /app /tmp/codex-home 2>/dev/null | head -50 && ls -lh /app/data && sed -n '1,240p' /app/data/README.txt && sed -n '1,260p' /app/data/itrek_frames.urdf"
```

## cmd 2 (exit 0)
```
"which ros2 || true
which mcap || true
which pcl_viewer || true
python3 - <<'PY'
mods=['mcap','mcap_ros2','rosbags','rclpy','sensor_msgs_py','numpy','scipy','open3d','laspy','plyfile','sklearn','numba','pyarrow']
for m in mods:
 try:
  x=__import__(m); print(m,'OK',getattr(x,'__version__',''))
 except Exception as e: print(m,'NO',type(e).__name__,str(e)[:120])
PY
df -h /app /tmp
find /opt/ros -maxdepth 3 -type f -name 'ros2' 2>/dev/null | head"
```

## message
The dataset includes a 10 Hz GNSS/INS pose stream, so the fixed-world trajectory can be obtained without accumulating wheel-odometry drift. I’m now checking exact message timing and pose conventions, then I’ll compare direct odometry and TF-derived poses before committing the trajectory.

## cmd 3 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
p='/app/data/orbit.mcap'
with open(p,'rb') as f:
 r=make_reader(f)
 s=r.get_summary()
 print('start/end/ns',s.statistics.message_start_time,s.statistics.message_end_time,(s.statistics.message_end_time-s.statistics.message_start_time)/1e9)
 print('messages',s.statistics.message_count)
 for cid,c in sorted(s.channels.items()):
  print(cid,c.topic,c.message_encoding,'schema',c.schema_id,'count',s.statistics.channel_message_counts.get(cid))
 for sid,sch in sorted(s.schemas.items()):
  print('schema',sid,sch.name,sch.encoding,len(sch.data))
PY"
```

## cmd 4 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
p='/app/data/orbit.mcap'
with open(p,'rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for sch,ch,msg,ros in r.iter_decoded_messages(topics=['/fixposition/odometry_enu']):
  print(type(ros),ros); break
with open(p,'rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for sch,ch,msg,ros in r.iter_decoded_messages(topics=['/fused_points']):
  print(type(ros)); print(ros); break
PY"
```

## cmd 5 (exit 0)
```
"ps -eo pid,etime,pcpu,pmem,cmd | rg '[p]ython3 -'"
```

## cmd 6 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
from collections import Counter,defaultdict
import numpy as np
p='/app/data/orbit.mcap'
for topic in ['/fixposition/odometry_enu','/fused_points','/tf']:
 ts=[]; logs=[]; dat=[]; frames=Counter()
 with open(p,'rb') as f:
  r=make_reader(f,decoder_factories=[DecoderFactory()])
  for sch,ch,msg,x in r.iter_decoded_messages(topics=[topic]):
   logs.append(msg.log_time/1e9)
   if topic=='/tf':
    for tr in x.transforms:
     frames[(tr.header.frame_id,tr.child_frame_id)]+=1
     if (tr.header.frame_id,tr.child_frame_id) in [('map','odom'),('odom','vrtk_link')]:
      t=tr.header.stamp.sec+tr.heade
```

## cmd 7 (exit 0)
```
'while kill -0 4949 2>/dev/null; do sleep 2; done'
```

## cmd 8 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
import numpy as np
p='/app/data/orbit.mcap'; ts=[]; logs=[]; dat=[]
with open(p,'rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for _,_,msg,x in r.iter_decoded_messages(topics=['/fixposition/odometry_enu']):
  logs.append(msg.log_time/1e9); ts.append(x.header.stamp.sec+x.header.stamp.nanosec*1e-9)
  p0=x.pose.pose.position; q=x.pose.pose.orientation; v=x.twist.twist.linear
  dat.append([p0.x,p0.y,p0.z,q.x,q.y,q.z,q.w,v.x,v.y,v.z])
t=np.array(ts); l=np.array(logs); a=np.array(dat)
print('n/log/stamp',len(t),[l.min(),l.max()],[t.min(),t.max()])
print('stamp dt p',np.percentile
```

## cmd 9 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
import numpy as np
p='/app/data/orbit.mcap'; a=[]
with open(p,'rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for i,(_,_,_,x) in enumerate(r.iter_decoded_messages(topics=['/fixposition/odometry_enu'])):
  if i%50==0:
   p0=x.pose.pose.position; q=x.pose.pose.orientation
   yaw=np.degrees(np.arctan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))
   print(i,f'{x.header.stamp.sec}.{x.header.stamp.nanosec:09d}',f'{p0.x:.3f} {p0.y:.3f} {p0.z:.3f} yaw {yaw:.2f}')
PY"
```

## cmd 10 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
from scipy.spatial.transform import Rotation
import numpy as np
ps=[]; gs=[]; zs=[]
with open('/app/data/orbit.mcap','rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for _,_,_,x in r.iter_decoded_messages(topics=['/fixposition/odometry_enu']):
  p=x.pose.pose.position;q=x.pose.pose.orientation
  P=np.array([p.x,p.y,p.z]); R=Rotation.from_quat([q.x,q.y,q.z,q.w])
  B=P+R.apply([-.173575,0,-.469325]); G=B+R.apply([0,0,-.1524])
  ps.append(B);gs.append(G)
g=np.array(gs); A=np.c_[g[:,0],g[:,1],np.ones(len(g))]; coef=np.linalg.lstsq(A,g[:,2],rcond=None)[0]; res=g[:,2]-A@coef
print(
```

## message
The GNSS/INS path is internally consistent and places `base_link` about 0.15 m above a gently sloped apron; fitting the robot’s footprint around the orbit gives an apron-plane residual of about 1.8 cm RMS. I’ll use that fixed metric frame, exclude near-ground returns by height above this plane, and use the enclosing orbit plus spatial connectivity to separate the aircraft from everything else.

## cmd 11 (exit 0)
```
'ls -l /app/reconstruct_aircraft.py && python3 -m py_compile /app/reconstruct_aircraft.py'
```

## cmd 12 (exit 0)
```
'python3 /app/reconstruct_aircraft.py --mode trajectory'
```

## cmd 13 (exit 0)
```
'python3 /app/reconstruct_aircraft.py --mode coarse --bounds -76 -28 -8 35'
```

## cmd 14 (exit 0)
```
"python3 - <<'PY'
import open3d as o3d, numpy as np
p=np.asarray(o3d.io.read_point_cloud('/app/coarse_above.ply').points)
print('n',len(p),'min',p.min(0),'max',p.max(0),'mean',p.mean(0))
zplane=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097
h=p[:,2]-zplane
print('height pct',np.percentile(h,[0,1,5,10,25,50,75,90,95,99,100]))
for lo,hi in [(0.25,.4),(.4,.6),(.6,1),(1,2),(2,4),(4,8),(8,16)]:
 m=(h>=lo)&(h<hi); print('h',lo,hi,m.sum(),'xy',p[m,:2].min(0) if m.any() else None,p[m,:2].max(0) if m.any() else None)
# Coarse projected occupancy summaries in 2m cells.
ix=np.floor((p[:,0]+80)/2).astype(int); iy=np.floor((p[:,1]+10)/2).astype(int)
for min_h in [.25,.5,1,2,4]:
 m=h>=min_h; u,c=np.uni
```

## cmd 15 (exit 0)
```
"python3 - <<'PY'
import open3d as o3d, numpy as np
import matplotlib.pyplot as plt
p=np.asarray(o3d.io.read_point_cloud('/app/coarse_above.ply').points)
plane=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097
h=p[:,2]-plane
rng=np.random.default_rng(4)
idx=rng.choice(len(p),min(180000,len(p)),replace=False); s=p[idx]; sh=h[idx]
fig,ax=plt.subplots(2,2,figsize=(16,13),dpi=150)
a=ax[0,0].scatter(s[:,0],s[:,1],c=np.clip(sh,0,8),s=.25,cmap='turbo'); ax[0,0].set_aspect('equal'); ax[0,0].set_title('top, color=height'); fig.colorbar(a,ax=ax[0,0])
for lo,hi,a0 in [(.25,1,ax[0,1]),(1,4,ax[1,0]),(4,16,ax[1,1])]:
 m=(sh>=lo)&(sh<hi); a0.scatter(s[m,0],s[m,1],s=.3); a0.set_aspect('equal');a0.set_title(
```

## cmd 16 (exit 0)
```
"python3 - <<'PY'
import open3d as o3d, numpy as np, time
pc=o3d.io.read_point_cloud('/app/coarse_above.ply'); p=np.asarray(pc.points)
plane=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097; h=p[:,2]-plane
m=(p[:,0]>=-70)&(p[:,0]<=-36)&(p[:,1]>=-4)&(p[:,1]<=28)&(h>=.35)&(h<=12)
p=p[m]; print('crop n',len(p),'bounds',p.min(0),p.max(0))
for eps,minp in [(.15,3),(.20,3),(.25,4)]:
 q=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(p)); t=time.time(); lab=np.asarray(q.cluster_dbscan(eps=eps,min_points=minp,print_progress=False)); u,c=np.unique(lab,return_counts=True); ii=np.argsort(c)[-12:][::-1]
 print('params',eps,minp,'sec',time.time()-t,'clusters',len(u)-(-1 in u),'noise',(lab<0).sum(),'l
```

## cmd 17 (exit 0)
```
'free -h'
```

## cmd 18 (exit 0)
```
'python3 -m py_compile /app/reconstruct_aircraft.py && python3 /app/reconstruct_aircraft.py --mode map --output /app/final_crop.ply --bounds -71 -35 -5 29 --min-height 0.30 --max-height 12 --voxel 0.04 --min-observations 1 --save-npz'
```

## message
The dense pass retained about 2.06 million 4 cm voxels in a deliberately broad crop. Repeated-view support is a strong separator here: half the voxels occur in only one scan, while the aircraft surfaces are repeatedly observed. I’m evaluating support thresholds and 3-D connected components now so that sparse transient returns and the robot’s own moving footprint are excluded without trimming wing, tail, engine, or landing-gear surfaces.

## cmd 19 (exit 0)
```
"python3 - <<'PY'
import numpy as np, matplotlib.pyplot as plt
d=np.load('/app/final_crop.npz');p=d['points'];o=d['observations']
pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097; h=p[:,2]-pl
print('n/bounds',len(p),p.min(0),p.max(0)); print('obs distribution',[(k,int((o>=k).sum())) for k in [1,2,3,4,5,8,10,15,20,30]])
for k in [1,2,3,5,10]:
 m=o>=k; print('obs>=',k,'n',m.sum(),'height percentiles',np.percentile(h[m],[0,1,10,50,90,99,100]))
rng=np.random.default_rng(9); fig,ax=plt.subplots(2,2,figsize=(16,14),dpi=150)
for k,a in zip([1,2,3,5],ax.ravel()):
 ids=np.flatnonzero(o>=k); ids=rng.choice(ids,min(250000,len(ids)),replace=False); s=p[ids]; sh=h[ids]
 q=a.scatter(s[:,0],s[:,1],c=np
```

## cmd 20 (exit 0)
```
'python3 /app/reconstruct_aircraft.py --mode coarse --output /app/coarse_r3.ply --bounds -76 -28 -8 35 --min-range 3'
```

## cmd 21 (exit 0)
```
"python3 - <<'PY'
import open3d as o3d,numpy as np,matplotlib.pyplot as plt
p=np.asarray(o3d.io.read_point_cloud('/app/coarse_r3.ply').points);pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097;h=p[:,2]-pl
fig,ax=plt.subplots(figsize=(10,10),dpi=140);q=ax.scatter(p[:,0],p[:,1],c=np.clip(h,0,8),s=.2,cmap='turbo');ax.set_aspect('equal');ax.set_xlim(-76,-28);ax.set_ylim(-8,35);fig.colorbar(q);fig.tight_layout();fig.savefig('/app/coarse_r3.png')
PY"
```

## cmd 22 (exit 0)
```
"python3 - <<'PY'
import numpy as np
d=np.load('/app/final_crop.npz');p=d['points'];o=d['observations'];pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097;h=p[:,2]-pl
for k in [2,3,5]:
 print('\\nOBS',k)
 m=(o>=k)&(p[:,1]>8)&(p[:,1]<16)
 for x0 in np.arange(-71,-35,.5):
  z=h[m&(p[:,0]>=x0)&(p[:,0]<x0+.5)]
  if len(z)>100: print(f'x {x0:5.1f} n {len(z):5d} hp {np.percentile(z,[5,25,50,75,95]).round(2)}')
PY"
```

## cmd 23 (exit 0)
```
"python3 - <<'PY'
import numpy as np, matplotlib.pyplot as plt
from scipy.spatial import cKDTree
d=np.load('/app/final_crop.npz');p=d['points'];o=d['observations'];tr=np.loadtxt('/app/trajectory.tum'); dist=cKDTree(tr[:,1:3]).query(p[:,:2],workers=-1)[0]
pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097;h=p[:,2]-pl
print('dist percentiles all',np.percentile(dist,[0,1,5,10,25,50,75,90,99,100]))
fig,ax=plt.subplots(2,2,figsize=(16,14),dpi=150); rng=np.random.default_rng(19)
for cutoff,a in zip([.5,1,1.5,2],ax.ravel()):
 ids=np.flatnonzero((o>=2)&(dist>=cutoff));ids=rng.choice(ids,min(300000,len(ids)),False);s=p[ids];sh=h[ids]
 q=a.scatter(s[:,0],s[:,1],c=np.clip(sh,0,10),s=.2,cmap='turbo');
```

## cmd 24 (exit 0)
```
"python3 - <<'PY'
import open3d as o3d,numpy as np,time
d=np.load('/app/final_crop.npz'); p=d['points'];o=d['observations'];pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097;h=p[:,2]-pl
for obs,eps,minp in [(2,.08,3),(2,.12,3),(3,.10,3),(3,.15,3)]:
 m=(o>=obs)&(p[:,0]>=-68)&(p[:,0]<=-36.5)&(p[:,1]>=-3)&(p[:,1]<=28)&(h<=11.5)
 q=p[m]; print('\\ninput',obs,eps,len(q));pc=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(q));t=time.time();lab=np.asarray(pc.cluster_dbscan(eps=eps,min_points=minp,print_progress=False));print('sec',time.time()-t)
 u,c=np.unique(lab,return_counts=True);ii=np.argsort(c)[-15:][::-1];print('cluster/noise',len(u)-(-1 in u),(lab<0).sum(),[(int(u[j]),int(c[j])) for j
```

## cmd 25 (exit 0)
```
"python3 - <<'PY'
import numpy as np,matplotlib.pyplot as plt
d=np.load('/app/final_crop.npz');p=d['points'];o=d['observations'];pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097;h=p[:,2]-pl
fig,ax=plt.subplots(3,3,figsize=(18,18),dpi=140);bins=[(.3,.6),(.6,1),(1,1.5),(1.5,2),(2,2.5),(2.5,3),(3,4),(4,6),(6,9)]
for (lo,hi),a in zip(bins,ax.ravel()):
 m=(o>=3)&(h>=lo)&(h<hi);a.scatter(p[m,0],p[m,1],s=.15);a.set_aspect('equal');a.set_xlim(-70,-36);a.set_ylim(-4,29);a.set_title(f'{lo} <= h < {hi}, n={m.sum():,}')
fig.tight_layout();fig.savefig('/app/height_slices.png')
PY"
```

## cmd 26 (exit 0)
```
"python3 - <<'PY'
import open3d as o3d,numpy as np,matplotlib.pyplot as plt,time
d=np.load('/app/final_crop.npz');p=d['points'];o=d['observations'];pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097;h=p[:,2]-pl
m=(o>=2)&(p[:,0]>=-66)&(p[:,0]<=-38)&(p[:,1]>=-2)&(p[:,1]<=28)&(h<=8.5)
q=p[m]; qo=o[m]; qh=h[m];pc=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(q));lab=np.asarray(pc.cluster_dbscan(eps=.08,min_points=3,print_progress=False));u,c=np.unique(lab[lab>=0],return_counts=True);main=u[np.argmax(c)];sel=lab==main
print('candidate/main/noise',len(q),sel.sum(),(lab<0).sum(),'bbox',q[sel].min(0),q[sel].max(0),'h',qh[sel].min(),qh[sel].max())
fig,ax=plt.subplots(2,2,figsize=(16,14),dpi=15
```

## cmd 27 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
from scipy.spatial.transform import Rotation
import numpy as np
edges={}
with open('/app/data/orbit.mcap','rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for _,_,_,msg in r.iter_decoded_messages(topics=['/tf']):
  for x in msg.transforms:
   edge=(x.header.frame_id,x.child_frame_id)
   if edge not in [('map','odom'),('odom','vrtk_link')]:continue
   ns=x.header.stamp.sec*10**9+x.header.stamp.nanosec;t=x.transform.translation;q=x.transform.rotation
   edges.setdefault(ns,{})[edge]=(np.array([t.x,t.y,t.z]),Rotation.from_quat([q.x,q.y,q.z,q.w]))
direct={}
with open('/app/data/o
```

## message
The direct odometry and the recorded `map → odom → vrtk_link` TF chain agree to numerical precision, confirming the trajectory convention and lever arm. The current aircraft component is clean and complete. I’m doing one additional accuracy check using the raw per-point timestamps: if their timing is reliable, I can de-skew the aircraft model itself while keeping it in exactly the same world frame as the required trajectory.

## cmd 28 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
import numpy as np
for topic in ['/hesai/points','/livox/lidar']:
 with open('/app/data/orbit.mcap','rb') as f:
  r=make_reader(f,decoder_factories=[DecoderFactory()])
  for _,_,rec,x in r.iter_decoded_messages(topics=[topic]):
   print('\\n',topic,'frame',x.header.frame_id,'header',f'{x.header.stamp.sec}.{x.header.stamp.nanosec:09d}','log',rec.log_time/1e9,'w/h/step',x.width,x.height,x.point_step)
   print('fields',[(z.name,z.offset,z.datatype,z.count) for z in x.fields])
   names=[];fmts=[];offs=[]
   typefmt={1:'i1',2:'u1',3:'<i2',4:'<u2',5:'<i4',6:'<u4',7:'<f4',8:'<f8'}
   for z in x.fields
```

## cmd 29 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
import numpy as np
for topic in ['/hesai/points','/livox/lidar']:
 with open('/app/data/orbit.mcap','rb') as f:
  r=make_reader(f,decoder_factories=[DecoderFactory()])
  for i,(_,_,rec,x) in enumerate(r.iter_decoded_messages(topics=[topic])):
   dt=np.dtype({'names':['x','y','z','i','a','b','t'],'formats':['<f4','<f4','<f4','<f4','<u2' if 'hesai' in topic else 'u1','u1' if 'livox' in topic else '<f8','<f8'],'offsets':[0,4,8,12,16,17 if 'livox' in topic else 18,18], 'itemsize':26}) if False else np.dtype({'names':['x','y','z','t'],'formats':['<f4','<f4','<f4','<f8'],'offsets':[0,4,8,18],'itemsiz
```

## cmd 30 (exit 0)
```
'python3 -m py_compile /app/reconstruct_aircraft.py && python3 /app/reconstruct_aircraft.py --mode raw --output /app/raw_deskewed.ply --bounds -68 -38 -2 28 --min-height 0.30 --max-height 9 --voxel 0.04 --min-observations 1 --min-range 1.5 --time-bin-ms 2 --save-npz'
```

## cmd 31 (exit 0)
```
"python3 - <<'PY'
import open3d as o3d,numpy as np,time
for file in ['/app/raw_deskewed.npz','/app/final_crop.npz']:
 d=np.load(file);p=d['points'];o=d['observations'];pl=.00158866177*p[:,0]-.00998869046*p[:,1]-.53477097;h=p[:,2]-pl
 print('\\n',file,'all',len(p),[(k,int((o>=k).sum())) for k in [2,3,5,10]])
 for obs in [2,3]:
  m=(o>=obs)&(p[:,0]>=-66)&(p[:,0]<=-38)&(p[:,1]>=-2)&(p[:,1]<=28)&(h<=8.5)
  q=p[m]; qo=o[m];qh=h[m];pc=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(q));t=time.time();lab=np.asarray(pc.cluster_dbscan(eps=.08,min_points=3,print_progress=False));u,c=np.unique(lab[lab>=0],return_counts=True);ii=np.argsort(c)[-5:][::-1]
  print('obs',obs,'cand',len(q),'noise',(lab<0)
```

## cmd 32 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
from scipy.spatial.transform import Rotation,Slerp
import numpy as np
tr=np.loadtxt('/app/trajectory.tum');t0=tr[0,0];ts=tr[:,0]-t0;pos=tr[:,1:4];sl=Slerp(ts,Rotation.from_quat(tr[:,4:8]));vals=[]
with open('/app/data/orbit.mcap','rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for i,(_,_,_,m) in enumerate(r.iter_decoded_messages(topics=['/fused_points'])):
  if i%20:continue
  local=np.frombuffer(m.data,dtype='<f4').reshape(-1,3)[::10];good=np.isfinite(local).all(1);r2=np.einsum('ij,ij->i',local,local);good&=(r2>4)&(r2<900);local=local[good]
  t=m.header.stamp.sec+m.header.s
```

## cmd 33 (exit 0)
```
'python3 -m py_compile /app/reconstruct_aircraft.py && python3 /app/reconstruct_aircraft.py --mode segment'
```

## message
The de-skewed raw-sensor reconstruction produced a single connected aircraft component with 640,568 points, spanning 27.1 × 28.8 m and 7.1 m above its lowest returns. I’ve written the required PLY and am now running format, timestamp, quaternion, apron-clearance, and cross-reprojection consistency checks against an independently accumulated `/fused_points` model.

## cmd 34 (exit 0)
```
"python3 - <<'PY'
from pathlib import Path
import struct
import numpy as np, open3d as o3d
from scipy.spatial import cKDTree
# TUM checks
lines=[x for x in Path('/app/trajectory.tum').read_text().splitlines() if x and not x.startswith('#')]
a=np.array([[float(y) for y in x.split()] for x in lines]); stamps=[x.split()[0] for x in lines]
print('TUM lines/cols',len(lines),a.shape[1],'ascending',bool(np.all(np.diff(a[:,0])>0)),'finite',bool(np.isfinite(a).all()))
print('TUM first/last',lines[0],lines[-1]);print('quat norm min/max',np.linalg.norm(a[:,4:8],axis=1).min(),np.linalg.norm(a[:,4:8],axis=1).max(),'nanosecond digits',sorted(set(len(s.split('.')[1]) for s in stamps)))
# PLY binary structu
```

## message
Completed:

- [trajectory.tum](/app/trajectory.tum) — 1,462 timestamped poses
- [aircraft.ply](/app/aircraft.ply) — 640,568 aircraft points, binary little-endian PLY

Validated timestamps, quaternion norms, binary structure, shared-frame centroid/heading, and apron clearance.

