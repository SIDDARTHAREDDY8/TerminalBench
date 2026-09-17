# codex trial 1 — command and message summary

## message
I’ll first inventory the recording, calibration, and available ROS/point-cloud tooling. Then I’ll reconstruct a closed-loop trajectory, validate scan consistency, and extract the above-apron aircraft surface into the required PLY.

## cmd 1 (exit 0)
```
"ls -lh /app/data && sed -n '1,240p' /app/data/README.txt && sed -n '1,260p' /app/data/itrek_frames.urdf && command -v ros2 || true && command -v pcl_viewer || true && python3 - <<'PY'
mods=['mcap','mcap_ros2','numpy','scipy','open3d','rosbags','sklearn','laspy']
for m in mods:
 try:
  x=__import__(m); print(m,'OK',getattr(x,'__version__',''))
 except Exception as e: print(m,'NO',str(e))
PY"
```

## cmd 2 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
p='/app/data/orbit.mcap'
with open(p,'rb') as f:
 r=make_reader(f)
 s=r.get_summary()
 print('start/end',s.statistics.message_start_time,s.statistics.message_end_time,(s.statistics.message_end_time-s.statistics.message_start_time)/1e9)
 for cid,c in s.channels.items(): print(cid,c.topic,c.message_encoding,s.statistics.channel_message_counts.get(cid), 'schema',c.schema_id)
 for sid,sc in s.schemas.items(): print('SCHEMA',sid,sc.name,sc.encoding,len(sc.data))
PY"
```

## cmd 3 (exit 0)
```
"python3 - <<'PY'
from mcap_ros2.reader import read_ros2_messages
for x in read_ros2_messages('/app/data/orbit.mcap',topics=['/fixposition/odometry_enu']):
 print(type(x),x)
 print(x.ros_msg)
 break
PY"
```

## message
The recording contains 1,462 fused scans and a high-quality GNSS/INS pose stream with centimetre-scale reported covariance. I’ll use that absolute pose as the drift-free backbone, interpolate it at the exact scan stamps, and apply the calibrated `vrtk_link → base_link` offset. I’m now checking timing, loop geometry, and scene height so the aircraft can be separated without retaining apron points.

## cmd 4 (exit 0)
```
"ls -la /app && python3 - <<'PY'
from mcap_ros2.reader import read_ros2_messages
import numpy as np
from scipy.spatial.transform import Rotation
p='/app/data/orbit.mcap'
for topic in ['/fixposition/odometry_enu','/fused_points']:
 ts=[]; log=[]; vals=[]
 for x in read_ros2_messages(p,topics=[topic]):
  m=x.ros_msg; ts.append(m.header.stamp.sec+m.header.stamp.nanosec*1e-9); log.append(x.log_time_ns*1e-9)
  if topic.startswith('/fix'): vals.append([m.pose.pose.position.x,m.pose.pose.position.y,m.pose.pose.position.z,m.pose.pose.orientation.x,m.pose.pose.orientation.y,m.pose.pose.orientation.z,m.pose.pose.orientation.w, m.pose.covariance[0],m.pose.covariance[7],m.pose.covariance[14]])
 ts=np.array(ts);log=np.array(log)
 print(topic,len(ts),'stamp',repr(ts[0]),repr(ts[-1]),'dt min/max/med',np.diff(ts).min(),np.diff(ts).max(),np.median(np.diff(ts)),'log-stamp range', (log-ts).min(),(log-ts).m
```

## cmd 5 (exit 0)
```
"python3 - <<'PY'
from mcap_ros2.reader import read_ros2_messages
import numpy as np
for x in read_ros2_messages('/app/data/orbit.mcap',topics=['/fused_points']):
 m=x.ros_msg
 print(type(m.data),len(m.data),m.width,m.height,m.point_step,m.row_step,m.is_bigendian,m.is_dense)
 print(m.fields)
 a=np.frombuffer(m.data,dtype='<f4').reshape(-1,3)
 print(a.shape,'finite',np.isfinite(a).all(1).sum(),'minmax',np.nanmin(a,0),np.nanmax(a,0),'sample',a[:3])
 break
PY"
```

## cmd 6 (exit 0)
```
'python3 /app/reconstruct.py trajectory && python3 /app/reconstruct.py diagnostics --every 10'
```

## cmd 7 (exit 0)
```
"python3 - <<'PY'
import numpy as np
D=np.load('/app/diagnostic_scene.npz'); p=D['scene']; path=D['path']
print('path bounds',path.min(0),path.max(0),'mean',path.mean(0))
# bounded scene around orbit
m=(p[:,0]>path[:,0].min()-5)&(p[:,0]<path[:,0].max()+5)&(p[:,1]>path[:,1].min()-5)&(p[:,1]<path[:,1].max()+5)&(p[:,2]>-3)&(p[:,2]<20)
q=p[m]
print('bounded',len(q),'xyz minmax',q.min(0),q.max(0))
h,e=np.histogram(q[:,2],bins=np.arange(-2,20,.05));
for i in np.argsort(h)[-20:][::-1]:print('z',e[i],e[i+1],h[i])
print('z percentiles',np.percentile(q[:,2],[0,1,5,10,25,50,75,90,95,99,100]))
PY
python3 - <<'PY'
import numpy as np, matplotlib.pyplot as plt
D=np.load('/app/diagnostic_scene.npz'); p=D['scene']; path=D['path']
rng=np.random.default_rng(1)
m=(p[:,0]>-80)&(p[:,0]<-25)&(p[:,1]>-12)&(p[:,1]<38)&(p[:,2]>-.60)&(p[:,2]<18)
q=p[m]
if len(q)>500000:q=q[rng.choice(len(q),500000,replace=False)]

```

## cmd 8 (exit 0)
```
"python3 - <<'PY'
import numpy as np
D=np.load('/app/diagnostic_scene.npz');p=D['path']
A=np.c_[p[:,:2],np.ones(len(p))];coef=np.linalg.lstsq(A,p[:,2]-.1524,rcond=None)[0];res=A@coef-(p[:,2]-.1524)
print('ground plane z=',coef,'res rmse',np.sqrt(np.mean(res**2)),'percentile',np.percentile(res,[0,1,5,50,95,99,100]))
# smooth residual/time range
for n in [0,100,200,400,600,800,1000,1200,1400]: print(n,p[n],A[n]@coef,res[n])
PY"
```

## message
The projected sample already resolves the fuselage, swept wings, and tail cleanly in the ENU frame. The apron is a consistent plane with about a 1% slope; after fitting that plane, the robot’s inferred height has only ~1.8 cm RMS residual. I’ll use height above this plane—not a global z cutoff—to preserve the aircraft’s low surfaces while enforcing the apron-exclusion requirement.

## cmd 9 (exit 0)
```
"python3 - <<'PY'
import numpy as np, matplotlib.pyplot as plt
D=np.load('/app/diagnostic_scene.npz');p=D['scene'];path=D['path']
A=np.c_[path[:,:2],np.ones(len(path))];coef=np.linalg.lstsq(A,path[:,2]-.1524,rcond=None)[0]
h=p[:,2]-(p[:,0]*coef[0]+p[:,1]*coef[1]+coef[2])
m=(p[:,0]>-76)&(p[:,0]<-28)&(p[:,1]>-8)&(p[:,1]<34)&(h>.28)&(h<16)
q=p[m];qh=h[m]
print('elevated count',len(q),'bounds',q.min(0),q.max(0),'h pct',np.percentile(qh,[0,1,5,25,50,75,95,99,100]))
rng=np.random.default_rng(3)
if len(q)>900000:
 idx=rng.choice(len(q),900000,replace=False);q=q[idx];qh=qh[idx]
fig,axs=plt.subplots(2,1,figsize=(14,15),dpi=160)
s=axs[0].scatter(q[:,0],q[:,1],c=qh,s=.18,cmap='turbo',vmin=.28,vmax=8,rasterized=True)
axs[0].plot(path[:,0],path[:,1],'k-',lw=.7);axs[0].set_aspect('equal');axs[0].set_xlim(-76,-28);axs[0].set_ylim(-8,34);fig.colorbar(s,ax=axs[0],label='height above apron [m]')
# x-heigh
```

## cmd 10 (exit 0)
```
'free -h && du -h /app/diagnostic_scene.npz /app/trajectory.tum && head -3 /app/trajectory.tum && tail -2 /app/trajectory.tum'
```

## cmd 11 (exit 0)
```
"python3 - <<'PY'
import numpy as np, open3d as o3d, time
D=np.load('/app/diagnostic_scene.npz');p=D['scene'].astype(np.float64);path=D['path'].astype(np.float64)
coef=np.linalg.lstsq(np.c_[path[:,:2],np.ones(len(path))],path[:,2]-.1524,rcond=None)[0]
h=p[:,2]-(p[:,0]*coef[0]+p[:,1]*coef[1]+coef[2])
m=(p[:,0]>-72)&(p[:,0]<-36)&(p[:,1]>-3)&(p[:,1]<30)&(h>.34)&(h<12)
p=p[m];print('selected raw',len(p),p.min(0),p.max(0))
pc=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(p));pc=pc.voxel_down_sample(.08);print('voxel',len(pc.points))
t=time.time(); labels=np.asarray(pc.cluster_dbscan(eps=.18,min_points=3,print_progress=False));print('dbscan time',time.time()-t)
u,c=np.unique(labels,return_counts=True);ids=np.argsort(c)[::-1]
q=np.asarray(pc.points)
for j in ids[:20]:
 lab=u[j]; z=q[labels==lab];print(lab,c[j], 'bounds',z.min(0),z.max(0))
PY"
```

## cmd 12 (exit 0)
```
"python3 - <<'PY'
import numpy as np, open3d as o3d, sys
sys.path.insert(0,'/app');from reconstruct import write_ply
D=np.load('/app/diagnostic_scene.npz');p=D['scene'].astype(np.float64);path=D['path'].astype(np.float64)
coef=np.linalg.lstsq(np.c_[path[:,:2],np.ones(len(path))],path[:,2]-.1524,rcond=None)[0]
h=p[:,2]-(p[:,0]*coef[0]+p[:,1]*coef[1]+coef[2]);m=(p[:,0]>-72)&(p[:,0]<-36)&(p[:,1]>-3)&(p[:,1]<30)&(h>.34)&(h<12);p=p[m]
pc=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(p));pc=pc.voxel_down_sample(.06);labels=np.asarray(pc.cluster_dbscan(eps=.16,min_points=3));u,c=np.unique(labels[labels>=0],return_counts=True);lab=u[np.argmax(c)];q=np.asarray(pc.points)[labels==lab]
print('main',len(q),q.min(0),q.max(0));write_ply('/app/candidate.ply',q)
# internal nearest neighbor dist from random first vs last? voxel NN spacing
from scipy.spatial import cKDTree
rng=np.random.default_rng(1
```

## cmd 13 (exit 0)
```
"python3 - <<'PY'
import sys,time
sys.path.insert(0,'/app')
import numpy as np,open3d as o3d
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from mcap_ros2.reader import read_ros2_messages
from reconstruct import load_navigation,PoseInterpolator,stamp_ns,MCAP
# target candidate
b=open('/app/candidate.ply','rb').read();off=b.index(b'end_header\\n')+11;target_pts=np.frombuffer(b[off:],dtype='<f4').reshape(-1,3).astype(float)
target=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(target_pts));target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=.35,max_nn=40));tree=cKDTree(target_pts)
nt,np_,nq=load_navigation();interp=PoseInterpolator(nt,np_,nq);path_p=interp.at(nt)[0];coef=np.linalg.lstsq(np.c_[path_p[:,:2],np.ones(len(path_p))],path_p[:,2]-.1524,rcond=None)[0]
results=[];start=time.time()
for i,rec in enumerate(read_ros2_messages(MCAP,topi
```

## cmd 14 (exit 0)
```
"python3 - <<'PY'
import numpy as np,sys
from scipy.spatial.transform import Rotation
sys.path.insert(0,'/app');from reconstruct import *
a=np.loadtxt('/app/icp_test.txt');nt,p,q=load_navigation();interp=PoseInterpolator(nt,p,q);st=load_fused_stamps();bp,br=interp.at(st)
d=[]
for row in a:
 i=int(row[0]); tr=row[6:9]; rv=row[9:12]; dp=Rotation.from_rotvec(rv).apply(bp[i])+tr-bp[i];d.append(dp)
d=np.array(d)
print('actual dp percentiles',np.percentile(d,[0,10,50,90,100],axis=0));print('norm',np.percentile(np.linalg.norm(d,axis=1),[0,10,50,90,100]))
for row,di in zip(a,d):
 if row[2]<.82:print(int(row[0]),'before after',row[2:4], 'dp',di,'drdeg',np.degrees(row[9:12]))
PY"
```

## cmd 15 (exit 0)
```
"python3 - <<'PY'
import numpy as np,sys
from scipy.spatial.transform import Rotation
sys.path.insert(0,'/app');from reconstruct import *
a=np.loadtxt('/app/icp_test.txt');nt,p,q=load_navigation();interp=PoseInterpolator(nt,p,q);st=load_fused_stamps();bp,br=interp.at(st)
d=[]
for row in a:
 i=int(row[0]);dp=Rotation.from_rotvec(row[9:12]).apply(bp[i])+row[6:9]-bp[i];d.append(dp)
d=np.array(d)
print('actual dp percentiles',np.percentile(d,[0,10,50,90,100],axis=0));print('norm',np.percentile(np.linalg.norm(d,axis=1),[0,10,50,90,100]))
for row,di in zip(a,d):
 if row[2]<.82:print(int(row[0]),'before after',row[2:4], 'dp',di,'drdeg',np.degrees(row[9:12]))
PY"
```

## cmd 16 (exit 0)
```
"python3 - <<'PY'
from mcap_ros2.reader import read_ros2_messages
from collections import Counter
p='/app/data/orbit.mcap';c=Counter();n=0
for rec in read_ros2_messages(p,topics=['/tf']):
 for t in rec.ros_msg.transforms:
  c[(t.header.frame_id,t.child_frame_id)]+=1
  if (t.header.frame_id,t.child_frame_id) in [('map','odom'),('odom','vrtk_link')] and n<12:
   a=t.transform.translation;q=t.transform.rotation
   print(t.header.stamp.sec,t.header.stamp.nanosec,t.header.frame_id,t.child_frame_id,(a.x,a.y,a.z),(q.x,q.y,q.z,q.w));n+=1
print(c)
PY"
```

## message
A held-out-scan check against the reconstructed aircraft gives a median point-to-model residual around 4 cm, with roughly 87% of returns within 10 cm before any scan matching. That is comfortably above the requested precision threshold, so I’m keeping the GNSS/INS poses as the trajectory backbone rather than introducing unstable per-scan ICP corrections. I’m next using the raw per-point timestamps to see whether deskewing can sharpen the delivered aircraft cloud further.

## cmd 17 (exit 0)
```
"python3 - <<'PY'
from mcap_ros2.reader import read_ros2_messages
import numpy as np
for topic in ['/hesai/points','/livox/lidar']:
 for rec in read_ros2_messages('/app/data/orbit.mcap',topics=[topic]):
  m=rec.ros_msg
  print('\\n',topic,'header',m.header.stamp.sec,m.header.stamp.nanosec,'frame',m.header.frame_id,'n',m.width,'step',m.point_step,'len',len(m.data))
  for f in m.fields:print(f.name,f.offset,f.datatype,f.count)
  names=[];formats=[];offsets=[]
  mp={1:'i1',2:'u1',3:'<i2',4:'<u2',5:'<i4',6:'<u4',7:'<f4',8:'<f8'}
  for f in m.fields:names.append(f.name);formats.append(mp[f.datatype]);offsets.append(f.offset)
  dt=np.dtype({'names':names,'formats':formats,'offsets':offsets,'itemsize':m.point_step})
  a=np.frombuffer(m.data,dtype=dt)
  print('xyz minmax',[(np.nanmin(a[k]),np.nanmax(a[k])) for k in ['x','y','z']])
  print('ts minmax samples',repr(float(a['timestamp'].min())),rep
```

## cmd 18 (exit 0)
```
'PYTHONUNBUFFERED=1 python3 /app/reconstruct.py aircraft --voxel 0.05'
```

## cmd 19 (exit 0)
```
"python3 - <<'PY'
import numpy as np,matplotlib.pyplot as plt
b=open('/app/aircraft.ply','rb').read();o=b.index(b'end_header\\n')+11;p=np.frombuffer(b[o:],'<f4').reshape(-1,3);c=np.array([.00158888,-.00998861,-.5347736]);h=p[:,2]-(p[:,0]*c[0]+p[:,1]*c[1]+c[2]);rng=np.random.default_rng(3);i=rng.choice(len(p),min(800000,len(p)),False);q=p[i];qh=h[i]
fig,ax=plt.subplots(1,2,figsize=(15,7),dpi=160)
ax[0].scatter(q[:,0],q[:,1],c=qh,s=.12,cmap='turbo',vmin=.34,vmax=8);ax[0].set_aspect('equal');ax[0].set_xlim(-73,-35);ax[0].set_ylim(-4,31)
ax[1].scatter(q[:,0],qh,c=q[:,1],s=.12,cmap='coolwarm',vmin=-3,vmax=30);ax[1].set_xlim(-73,-35);ax[1].set_ylim(0,11);ax[1].set_aspect(1.7)
fig.tight_layout();fig.savefig('/app/raw_aircraft.png')
PY"
```

## cmd 20 (exit 0)
```
"ls -lh /app/raw_aircraft.png || true && python3 - <<'PY'
import numpy as np,matplotlib.pyplot as plt
b=open('/app/aircraft.ply','rb').read();o=b.index(b'end_header\\n')+11;p=np.frombuffer(b[o:],'<f4').reshape(-1,3);c=np.array([.00158888,-.00998861,-.5347736]);h=p[:,2]-(p[:,0]*c[0]+p[:,1]*c[1]+c[2]);rng=np.random.default_rng(3);i=rng.choice(len(p),min(600000,len(p)),False);q=p[i];qh=h[i]
fig,ax=plt.subplots(1,2,figsize=(15,7),dpi=140)
ax[0].scatter(q[:,0],q[:,1],c=qh,s=.12,cmap='turbo',vmin=.34,vmax=8);ax[0].set_aspect('equal');ax[0].set_xlim(-73,-35);ax[0].set_ylim(-4,31)
ax[1].scatter(q[:,0],qh,c=q[:,1],s=.12,cmap='coolwarm',vmin=-3,vmax=30);ax[1].set_xlim(-73,-35);ax[1].set_ylim(0,11);ax[1].set_aspect(1.7)
fig.tight_layout();fig.savefig('/app/raw_aircraft.png')
print(len(p))
PY"
```

## message
Per-point deskewing sharpened the aircraft, but processing every raw scan also made the robot’s own moving returns dense enough to connect to the aircraft component. I’ve isolated that failure mode: I’ll use the already-clean fused-scan aircraft as a geometric seed, retain deskewed returns only in its immediate surface neighborhood, and validate both residuals and silhouette before finalizing the PLY.

## cmd 21 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree

def read(p):
 b=open(p,'rb').read();o=b.index(b'end_header\\n')+11;return np.frombuffer(b[o:],'<f4').reshape(-1,3).copy()
seed=read('/app/candidate.ply');raw=read('/app/aircraft.ply')
t=cKDTree(seed);d=t.query(raw,workers=-1)[0]
print('raw->seed distance pct',np.percentile(d,[0,10,25,50,75,80,90,95,99,100]))
for x in [.08,.10,.12,.15,.18,.20,.25,.30]:
 q=raw[d<x];print(x,len(q),q.min(0),q.max(0))
d2=cKDTree(raw).query(seed,workers=-1)[0]
print('seed->raw',np.percentile(d2,[0,10,25,50,75,90,95,99,100]),'cov .1/.2',np.mean(d2<.1),np.mean(d2<.2))
PY"
```

## cmd 22 (exit 0)
```
"python3 - <<'PY'
import numpy as np, matplotlib.pyplot as plt
from scipy.spatial import cKDTree

def read(p):
 b=open(p,'rb').read();o=b.index(b'end_header\\n')+11;return np.frombuffer(b[o:],'<f4').reshape(-1,3).copy()
seed=read('/app/candidate.ply');raw=read('/app/aircraft.ply');d=cKDTree(seed).query(raw,workers=-1)[0];q=raw[d<.10]
for name,p in [('seed',seed),('raw10',q)]:
 cov=np.cov(p[:,:2].T);w,v=np.linalg.eigh(cov);ang=np.degrees(np.arctan2(v[1,-1],v[0,-1]));print(name,len(p),'centroid',p.mean(0),'pca angle',ang,'eig',w)
rng=np.random.default_rng(4);q=q[rng.choice(len(q),min(600000,len(q)),False)]
c=np.array([.00158888,-.00998861,-.5347736]);h=q[:,2]-(q[:,0]*c[0]+q[:,1]*c[1]+c[2])
fig,ax=plt.subplots(1,2,figsize=(15,6),dpi=150)
ax[0].scatter(q[:,0],q[:,1],c=h,s=.12,cmap='turbo',vmin=.34,vmax=8);ax[0].set_aspect('equal');ax[0].set_xlim(-71,-37);ax[0].set_ylim(-2,29)
ax[1].scatter(q
```

## cmd 23 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree

def read(p):
 b=open(p,'rb').read();o=b.index(b'end_header\\n')+11;return np.frombuffer(b[o:],'<f4').reshape(-1,3).copy()
s=read('/app/candidate.ply');r=read('/app/aircraft.ply');d=cKDTree(s).query(r,workers=-1)[0]
for x in [.06,.07,.08,.09,.10,.12,.15]:
 q=r[d<x]; ds=cKDTree(q).query(s,workers=-1)[0]
 print('thr',x,'n',len(q),'seed cov .1 .15 .2',np.mean(ds<.1),np.mean(ds<.15),np.mean(ds<.2),'med/p95/p99',np.percentile(ds,[50,95,99]))
PY"
```

## cmd 24 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree

def read(p):
 b=open(p,'rb').read();o=b.index(b'end_header\\n')+11;return np.frombuffer(b[o:],'<f4').reshape(-1,3).copy()
s=read('/app/candidate.ply');r=read('/app/aircraft.ply');d=cKDTree(s).query(r,workers=-1)[0];r=r[d<.08]
for x0,x1 in zip(range(-72,-36,3),range(-69,-33,3)):
 print(x0,x1,np.sum((s[:,0]>=x0)&(s[:,0]<x1)),np.sum((r[:,0]>=x0)&(r[:,0]<x1)))
for name,p in [('s',s),('r',r)]:
 for hmin in [.34,1,1.5,2,3]:
  c=np.array([.00159,-.00999,-.53477]);h=p[:,2]-(p[:,0]*c[0]+p[:,1]*c[1]+c[2]);q=p[h>hmin];print(name,hmin,len(q),q.mean(0))
PY"
```

## message
The clean seed retains more than 99.7% cross-coverage at 20 cm even when I restrict the deskewed cloud to an 8 cm surface neighborhood. I’m also reconstructing the complete `/fused_points` sequence now to measure its actual aircraft centroid and heading directly, so the final PLY remains consistent with the submitted trajectory rather than relying on a sparse-scan estimate.

## cmd 25 (exit 0)
```
"PYTHONUNBUFFERED=1 python3 - <<'PY'
import sys,time
sys.path.insert(0,'/app')
import numpy as np,open3d as o3d
from scipy.spatial import cKDTree
from mcap_ros2.reader import read_ros2_messages
from reconstruct import *
def readply(p):
 b=open(p,'rb').read();o=b.index(b'end_header\\n')+11;return np.frombuffer(b[o:],'<f4').reshape(-1,3).copy()
seed=readply('/app/candidate.ply');tree=cKDTree(seed)
nt,p,q=load_navigation();interp=PoseInterpolator(nt,p,q);apron=fit_apron_plane(interp,nt)
blocks=[];n=0
for i,rec in enumerate(read_ros2_messages(MCAP,topics=['/fused_points'])):
 m=rec.ros_msg;a=np.frombuffer(m.data,'<f4').reshape(-1,3);good=np.isfinite(a).all(1);rr=np.einsum('ij,ij->i',a,a);a=a[good&(rr>.25)&(rr<6400)].astype(float)
 bp,br=interp.at(stamp_ns(m.header.stamp));g=br.apply(a)+bp;g=g[aircraft_mask(g,apron,loose=False)]
 d=tree.query(g,workers=-1)[0];g=g[d<.12]
 blocks.append(g.astyp
```

## cmd 26 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree
def read(p):
 b=open(p,'rb').read();o=b.index(b'end_header\\n')+11;return np.frombuffer(b[o:],'<f4').reshape(-1,3).copy()
s=read('/app/candidate.ply');rawpool=read('/app/aircraft.ply');d=cKDTree(s).query(rawpool,workers=-1)[0];desk=rawpool[d<.08];fus=read('/app/fused_full_seed.ply')
for a,b,n in [(desk,fus,'desk->fused'),(fus,desk,'fused->desk')]:
 x=cKDTree(b).query(a,workers=-1)[0];print(n,len(a),'pct',np.percentile(x,[0,10,25,50,75,90,95,99,100]),'frac .05,.1,.2',np.mean(x<.05),np.mean(x<.1),np.mean(x<.2))
for name,p in [('desk',desk),('fused',fus)]:
 w,v=np.linalg.eigh(np.cov(p[:,:2].T));ang=np.degrees(np.arctan2(v[1,-1],v[0,-1]));print(name,'centroid',p.mean(0),'heading',ang,'eig',w)
PY"
```

## cmd 27 (exit 0)
```
"python3 - <<'PY'
import sys
sys.path.insert(0,'/app')
import numpy as np
from scipy.spatial import cKDTree
from reconstruct import write_ply

def read_ply(path):
    b=open(path,'rb').read(); off=b.index(b'end_header\\n')+len(b'end_header\\n')
    return np.frombuffer(b[off:],dtype='<f4').reshape(-1,3).copy()
seed=read_ply('/app/candidate.ply')
raw=read_ply('/app/aircraft.ply')
d=cKDTree(seed).query(raw,workers=-1)[0]
final=raw[d<0.08]
write_ply('/app/aircraft.ply',final)
print('final vertices',len(final),'centroid',final.mean(0),'bounds',final.min(0),final.max(0))
PY
python3 - <<'PY'
from pathlib import Path
import numpy as np
# trajectory validation
lines=[x for x in Path('/app/trajectory.tum').read_text().splitlines() if x and not x.startswith('#')]
a=np.array([[float(y) for y in x.split()] for x in lines])
assert a.shape==(1462,8),a.shape
assert np.isfinite(a).all()
assert np.all(np
```

## message
Completed and validated:

- [trajectory.tum](/app/trajectory.tum) — 1,462 poses, all fused scan stamps
- [aircraft.ply](/app/aircraft.ply) — binary little-endian PLY, 734,550 aircraft-only points

