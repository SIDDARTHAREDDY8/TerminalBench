# codex trial 3 — command and message summary

## message
I’ll first inventory the recording, calibration, and available ROS/point-cloud tooling. Then I’ll reconstruct and validate the orbit, explicitly separating the apron from the aircraft before writing the two required files.

## cmd 1 (exit 0)
```
"sed -n '1,240p' data/README.txt && printf '\\nFILES\\n' && ls -lh data && printf '\\nTOOLS\\n' && command -v ros2 || true && command -v mcap || true && command -v pcl_viewer || true && command -v python3 && python3 - <<'PY'
mods=['mcap','mcap_ros2','rosbags','open3d','numpy','scipy','sklearn','trimesh','cv2','pycpd','gtsam']
for m in mods:
 try:
  x=__import__(m); print(m, getattr(x,'__version__','ok'))
 except Exception as e: print(m, 'NO', type(e).__name__)
PY"
```

## message
The recording contains a strong absolute solution: 10 Hz GNSS–INS poses plus the missing rigid `vrtk_link → base_link` calibration. That should give the required metric, drift-free trajectory without relying on scan-matching drift. I’m now checking timestamp alignment and spatial extents before choosing the aircraft-only segmentation.

## cmd 2 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
p='data/orbit.mcap'
with open(p,'rb') as f:
 r=make_reader(f)
 s=r.get_summary()
 print('start/end',s.statistics.message_start_time,s.statistics.message_end_time)
 for c in sorted(s.channels.values(), key=lambda c:c.topic):
  print(c.id,c.topic,c.message_encoding,s.schemas[c.schema_id].name if c.schema_id else '')
 print('counts')
 for cid,n in s.statistics.channel_message_counts.items(): print(s.channels[cid].topic,n)
PY"
```

## cmd 3 (exit 0)
```
"python3 - <<'PY'
import inspect, mcap_ros2.decoder
print(inspect.getsource(mcap_ros2.decoder.DecoderFactory))
PY"
```

## cmd 4 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
with open('data/orbit.mcap','rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for schema,ch,msg,obj in r.iter_decoded_messages(topics=['/fixposition/odometry_enu','/fused_points']):
  print(ch.topic,msg.log_time,msg.publish_time, type(obj),obj)
  break
PY"
```

## cmd 5 (exit 0)
```
'python3 work_reconstruct.py odom'
```

## cmd 6 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
import numpy as np,time
st=time.time()
with open('data/orbit.mcap','rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for s,c,m,o in r.iter_decoded_messages(topics=['/fused_points']):
  print('elapsed',time.time()-st,'header',o.header,'hw',o.height,o.width,'step',o.point_step,o.row_step,'data',type(o.data),len(o.data), 'dense',o.is_dense)
  xyz=np.frombuffer(o.data,dtype='<f4').reshape(-1,3)
  finite=np.isfinite(xyz).all(1)
  print('finite',finite.sum(),xyz[finite].min(0),xyz[finite].max(0),np.quantile(np.linalg.norm(xyz[finite],axis=1),[0,.5,.9,.99,1]))
  break
PY"
```

## cmd 7 (exit 0)
```
"python3 - <<'PY'
import numpy as np
z=np.load('odom.npz'); p=z['base']; q=z['quats']; t=z['times'];
from scipy.spatial.transform import Rotation
r=Rotation.from_quat(q)
yaw=r.as_euler('zyx',degrees=True)[:,0]
for i in list(range(0,len(t),100))+[len(t)-1]: print(i,(t[i]-t[0])/1e9, *p[i], yaw[i])
print('xy mean',p[:,:2].mean(0),'median',np.median(p[:,:2],0))
PY"
```

## cmd 8 (exit 0)
```
'python3 work_reconstruct.py sample'
```

## message
The first globally transformed sample is internally coherent and spans the full orbit. I’m using top and side projections to identify the aircraft footprint and the local apron plane; the important next check is whether GNSS–INS vertical and heading consistency are already within the surface tolerances or need scan-based refinement.

## cmd 9 (exit 0)
```
"python3 - <<'PY'
import numpy as np
p=np.load('sample_world.npy')
print('N',len(p))
for rad in [15,20,25,30]:
 m=(abs(p[:,0]+51.1)<rad)&(abs(p[:,1]-12.3)<rad)
 print('rad',rad,'n',m.sum(),'zq',np.quantile(p[m,2],[0,.01,.05,.1,.25,.5,.75,.9,.95,.99,1]))
h,e=np.histogram(p[:,2],bins=np.arange(-2,15,.02))
ix=np.argsort(h)[-15:][::-1]
print('top z hist',[(round((e[i]+e[i+1])/2,3),int(h[i])) for i in ix])
PY
python3 - <<'PY'
try:
 import matplotlib; print('matplotlib',matplotlib.__version__)
except Exception as e: print(e)
PY"
```

## cmd 10 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from sklearn.linear_model import RANSACRegressor, LinearRegression
p=np.load('sample_world.npy')
# points spatially around orbit and likely low enough for apron
m=(p[:,2]<0.0)&(abs(p[:,0]+51)<35)&(abs(p[:,1]-12)<35)
x=p[m]
rng=np.random.default_rng(1); x=x[rng.choice(len(x),min(300000,len(x)),False)]
r=RANSACRegressor(estimator=LinearRegression(),min_samples=500,residual_threshold=.035,max_trials=100,random_state=1).fit(x[:,:2],x[:,2])
print('plane',r.estimator_.coef_,r.estimator_.intercept_,'inliers',r.inlier_mask_.mean())
h=p[:,2]-(p[:,:2]@r.estimator_.coef_+r.estimator_.intercept_)
print('hq',np.quantile(h,[0,.001,.01,.05,.1,.25,.5,.75,.9,.95,.99,.999,
```

## cmd 11 (exit 0)
```
"MPLBACKEND=Agg python3 - <<'PY'
import numpy as np, matplotlib.pyplot as plt
p=np.load('sample_world.npy'); h=np.load('sample_height.npy'); od=np.load('odom.npz')['base']
rng=np.random.default_rng(2)
fig,ax=plt.subplots(1,3,figsize=(21,7))
for a,lo in zip(ax[:2],[.25,.45]):
 m=(h>lo)&(h<10)&(p[:,0]>-80)&(p[:,0]<-25)&(p[:,1]>-12)&(p[:,1]<38)
 ids=np.flatnonzero(m); ids=ids[rng.choice(len(ids),min(250000,len(ids)),False)]
 sc=a.scatter(p[ids,0],p[ids,1],c=np.clip(h[ids],0,6),s=.25,cmap='turbo',rasterized=True)
 a.plot(od[:,0],od[:,1],'k-',lw=.8); a.set_aspect('equal'); a.set_title(f'top h>{lo}, N={m.sum()}'); a.set_xlim(-80,-25); a.set_ylim(-12,38); fig.colorbar(sc,ax=a)
m=(h>.25)&(h<10)&(p[:
```

## cmd 12 (exit 0)
```
"python3 - <<'PY'
import numpy as np,open3d as o3d,time
p=np.load('sample_world.npy');h=np.load('sample_height.npy')
m=(h>.35)&(h<12)&(p[:,0]>-73)&(p[:,0]<-35)&(p[:,1]>-5)&(p[:,1]<30)
x=p[m]; print('candidate',len(x))
pc=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(x))
t=time.time(); lab=np.array(pc.cluster_dbscan(eps=.25,min_points=4,print_progress=False));print('secs',time.time()-t)
u,c=np.unique(lab,return_counts=True); ids=np.argsort(c)[::-1]
for k in ids[:20]:
 l=u[k]; pts=x[lab==l];print(l,c[k],pts.min(0),pts.max(0))
np.savez('sample_clusters.npz',points=x,labels=lab)
PY"
```

## cmd 13 (exit 0)
```
"MPLBACKEND=Agg python3 - <<'PY'
import numpy as np,matplotlib.pyplot as plt
z=np.load('sample_clusters.npz'); p=z['points'];lab=z['labels'];p=p[lab==0]
# plane height use saved coeff
coef=np.array([.00203358,-.01025332]); inter=-.5330154
h=p[:,2]-(p[:,:2]@coef+inter)
fig,ax=plt.subplots(2,3,figsize=(18,10))
for a,(lo,hi) in zip(ax.ravel(),[(-68,-66),(-63,-61),(-59,-57),(-55,-53),(-51,-49),(-43,-41)]):
 m=(p[:,0]>lo)&(p[:,0]<hi)
 a.scatter(p[m,1],h[m],c=p[m,0],s=.3,rasterized=True,cmap='viridis');a.set_title(f'x {lo}:{hi} N={m.sum()}');a.set_xlim(-3,29);a.set_ylim(0,9);a.grid()
fig.tight_layout();fig.savefig('cross.png',dpi=160)
PY"
```

## cmd 14 (exit 0)
```
'free -h && df -h /app'
```

## cmd 15 (exit 0)
```
"python3 - <<'PY'
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
from scipy.spatial.transform import Rotation
import numpy as np
found={}
with open('data/orbit.mcap','rb') as f:
 r=make_reader(f,decoder_factories=[DecoderFactory()])
 for _,ch,_,o in r.iter_decoded_messages(topics=['/tf']):
  for t in o.transforms:
   k=(t.header.frame_id,t.child_frame_id)
   if k in [('map','odom'),('odom','vrtk_link')] and k not in found:
    tr=t.transform.translation; q=t.transform.rotation
    found[k]=(t.header.stamp.sec+t.header.stamp.nanosec*1e-9,np.array([tr.x,tr.y,tr.z]),Rotation.from_quat([q.x,q.y,q.z,q.w]))
  if len(found)==2: break
for k,(t,p,r) in found.items():
```

## cmd 16 (exit 0)
```
"rg -n -C 3 'vrtk_link|base_link' data/itrek_frames.urdf | head -80"
```

## cmd 17 (exit 0)
```
"head -c 300 sample_world.ply | sed -n '1,20p'"
```

## message
The calibration chain has been cross-checked against the recorded TF composition and matches numerically. The aircraft is also a single dominant above-apron 3-D component, which lets me avoid a loose rectangular crop. I’ll now build the full-resolution cloud with temporal-persistence filtering so robot self-returns and apron clutter do not leak into the aircraft model.

## cmd 18 (exit 0)
```
'python3 work_reconstruct.py reconstruct'
```

## message
The full pass completed: all 1,462 fused timestamps are represented, and the first aircraft-only model contains about 709k 4 cm voxels. Before finalizing, I’m validating file conformance and looking for multipath “halos,” moving-object traces, or disconnected components that could reduce 10 cm precision.

## cmd 19 (exit 0)
```
"python3 - <<'PY'
from pathlib import Path
import numpy as np
p=Path('trajectory.tum'); lines=p.read_text().splitlines();a=np.loadtxt(p)
print('trajectory lines/shape',len(lines),a.shape)
print('first',lines[0]); print('last',lines[-1]);
print('time ascending',np.all(np.diff(a[:,0])>0),'finite',np.isfinite(a).all(),'qnorm',np.linalg.norm(a[:,4:8],axis=1).min(),np.linalg.norm(a[:,4:8],axis=1).max())
with open('aircraft.ply','rb') as f:
 h=b''
 while not h.endswith(b'end_header\\n'):h+=f.readline()
 print(h.decode(),end='')
 data=np.fromfile(f,dtype='<f4').reshape(-1,3)
print('ply shape finite',data.shape,np.isfinite(data).all(),'bounds',data.min(0),data.max(0))
coef=np.array([.00203358,-.0102
```

## cmd 20 (exit 0)
```
"MPLBACKEND=Agg python3 - <<'PY'
import numpy as np,matplotlib.pyplot as plt
p=np.load('aircraft_points.npy');coef=np.array([.00203358,-.01025332]);h=p[:,2]-(p[:,:2]@coef-.5330154)
rng=np.random.default_rng(3); ids=rng.choice(len(p),min(len(p),500000),False)
fig,ax=plt.subplots(1,3,figsize=(20,7))
sc=ax[0].scatter(p[ids,0],p[ids,1],c=np.clip(h[ids],0,7),s=.25,cmap='turbo',rasterized=True);ax[0].set_aspect('equal');fig.colorbar(sc,ax=ax[0]);ax[0].set_title('full output top')
ax[1].scatter(p[ids,0],h[ids],c=p[ids,1],s=.25,cmap='viridis',rasterized=True);ax[1].set_ylim(0,9);ax[1].set_title('side')
ax[2].scatter(p[ids,1],h[ids],c=p[ids,0],s=.25,cmap='viridis',rasterized=True);ax[2].set_ylim(0,9)
```

## cmd 21 (exit 0)
```
'OMP_NUM_THREADS=4 python3 work_reconstruct.py icp_test'
```

## cmd 22 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree
z=np.load('persistent_candidates.npz');p=z['points'];o=z['observations']
s=np.load('sample_clusters.npz');seed=s['points'][s['labels']==0]
t=cKDTree(seed)
for n in [1,2,3,4,5,8,10]:
 x=p[o>=n]; d=t.query(x,workers=-1)[0];
 print('obs',n,'N',len(x),'within seed .1 .15 .24',*(np.mean(d<a) for a in [.1,.15,.24]),'dq',np.percentile(d,[50,75,90,95,99]))
 # seed coverage of candidate at thresholds
 q=cKDTree(x).query(seed,workers=-1)[0]
 print(' seed cover .1/.2',np.mean(q<.1),np.mean(q<.2),'q',np.percentile(q,[50,90,95,99,100]))
PY"
```

## cmd 23 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree
z=np.load('persistent_candidates.npz');p=z['points'];o=z['observations']
s=np.load('sample_clusters.npz');seed=s['points'][s['labels']==0]
coef=np.array([.00203358,-.01025332]);
def h(x): return x[:,2]-(x[:,:2]@coef-.5330154)
t=cKDTree(seed)
for obs in [2,3,4]:
 for near in [.12,.15,.18,.24]:
  m=(o>=obs)&(h(p)>.38);x=p[m];d=t.query(x,workers=-1)[0];x=x[d<near]
  sd=cKDTree(x).query(seed[h(seed)>.38],workers=-1)[0]
  print(obs,near,len(x),'seed cover .1/.15/.2',*(np.mean(sd<a) for a in [.1,.15,.2]),'fill>.12',np.sum(sd>.12))
PY"
```

## cmd 24 (exit 0)
```
'python3 work_reconstruct.py finalize && ls -lh aircraft.ply'
```

## cmd 25 (exit 0)
```
"MPLBACKEND=Agg python3 - <<'PY'
import numpy as np,matplotlib.pyplot as plt
p=np.load('aircraft_points.npy');coef=np.array([.00203358,-.01025332]);h=p[:,2]-(p[:,:2]@coef-.5330154)
fig,ax=plt.subplots(1,3,figsize=(20,7));ids=np.arange(len(p))
sc=ax[0].scatter(p[:,0],p[:,1],c=np.clip(h,0,7),s=.3,cmap='turbo',rasterized=True);ax[0].set_aspect('equal');fig.colorbar(sc,ax=ax[0]);
ax[1].scatter(p[:,0],h,c=p[:,1],s=.3,cmap='viridis',rasterized=True);ax[1].set_ylim(0,9)
ax[2].scatter(p[:,1],h,c=p[:,0],s=.3,cmap='viridis',rasterized=True);ax[2].set_ylim(0,9)
for a in ax:a.grid()
fig.tight_layout();fig.savefig('final2.png',dpi=160)
PY"
```

## message
The geometry check revealed one likely non-aircraft attachment directly ahead of the nose—a low rectangular return that became connected to the main component by proximity. I’m separating low-level components now so the final PLY retains landing gear but excludes any tug or ground-support equipment.

## cmd 26 (exit 0)
```
"python3 - <<'PY'
import numpy as np,open3d as o3d
p=np.load('aircraft_points.npy');coef=np.array([.00203358,-.01025332]);h=p[:,2]-(p[:,:2]@coef-.5330154)
for lim in [1.25,1.4,1.6]:
 x=p[(h>.38)&(h<lim)]
 pc=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(x)); lab=np.array(pc.cluster_dbscan(eps=.11,min_points=4,print_progress=False))
 u,c=np.unique(lab,return_counts=True);order=np.argsort(c)[::-1]
 print('\\nLIMIT',lim,'N',len(x))
 for j in order[:15]:
  if u[j]<0:continue
  q=x[lab==u[j]];hh=q[:,2]-(q[:,:2]@coef-.5330154)
  print(u[j],c[j],'xyz',np.round(q.min(0),2),np.round(q.max(0),2),'h',np.round([hh.min(),hh.max()],2))
PY"
```

## cmd 27 (exit 0)
```
"python3 - <<'PY'
import numpy as np
p=np.load('aircraft_points.npy');coef=np.array([.00203358,-.01025332]);h=p[:,2]-(p[:,:2]@coef-.5330154)
for lo,hi in [(.38,.8),(.8,1.2),(1.2,1.5),(1.5,2),(2,2.5),(2.5,3),(3,4),(4,9)]:
 q=p[(h>=lo)&(h<hi)]
 print(lo,hi,len(q),'xq',np.round(np.percentile(q[:,0],[0,.1,1,5,50,95,99,99.9,100]),2),'yq',np.round(np.percentile(q[:,1],[0,1,50,99,100]),2))
# x bin y/z ranges
for xlo in np.arange(-70,-58,.5):
 m=(p[:,0]>=xlo)&(p[:,0]<xlo+.5);q=h[m]
 if len(q): print(round(xlo,1),len(q),np.round(np.percentile(q,[0,1,10,25,50,75,90,99,100]),2))
PY"
```

## cmd 28 (exit 0)
```
'python3 work_reconstruct.py finalize'
```

## cmd 29 (exit 0)
```
"MPLBACKEND=Agg python3 - <<'PY'
import numpy as np,matplotlib.pyplot as plt
p=np.load('aircraft_points.npy');c=np.array([.00203358,-.01025332]);h=p[:,2]-(p[:,:2]@c-.5330154)
fig,ax=plt.subplots(1,2,figsize=(15,6));ax[0].scatter(p[:,0],h,s=.3,rasterized=True);ax[0].set_ylim(0,8.5);ax[0].grid();ax[1].scatter(p[:,0],p[:,1],c=h,s=.3,rasterized=True,cmap='turbo');ax[1].set_aspect('equal');ax[1].grid();fig.tight_layout();fig.savefig('clean.png',dpi=150)
PY"
```

## cmd 30 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree
p=np.load('aircraft_points.npy');rng=np.random.default_rng(5);q=p[rng.choice(len(p),30000,False)]
d,ix=cKDTree(p).query(q,k=20,workers=-1)
x=p[ix]-p[ix].mean(1,keepdims=True)
c=np.einsum('nki,nkj->nij',x,x)/20
w=np.linalg.eigvalsh(c)
rough=np.sqrt(np.maximum(w[:,0],0))
print('knn radius',np.percentile(d[:,-1],[10,50,90,99]))
print('local roughness',np.percentile(rough,[10,25,50,75,90,95,99,100]))
PY"
```

## cmd 31 (exit 0)
```
"python3 - <<'PY'
import numpy as np
p=np.load('aircraft_points.npy');z=np.load('sample_clusters.npz');s=z['points'][z['labels']==0];c=np.array([.00203358,-.01025332]);h=s[:,2]-(s[:,:2]@c-.5330154);s=s[(h>.38)&~((s[:,0]<-63)&(h<1.45))]
for name,x in [('final',p),('sample',s)]:
 cov=np.cov(x[:,:2].T);w,v=np.linalg.eigh(cov);axis=v[:,np.argmax(w)];heading=np.degrees(np.arctan2(axis[1],axis[0]))
 print(name,len(x),'centroid',x.mean(0),'heading180',heading,'eig',w)
print('centroid distance',np.linalg.norm(p.mean(0)-s.mean(0)))
PY
python3 - <<'PY'
from pathlib import Path
import re,os,numpy as np
path=Path('aircraft.ply')
with path.open('rb') as f:
 header=b''
 while not header.endswith(b'end_hea
```

## cmd 32 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree
z=np.load('persistent_candidates.npz');p=z['points'];o=z['observations'];s=np.load('sample_clusters.npz');s=s['points'][s['labels']==0];c=np.array([.00203358,-.01025332]);
def h(x):return x[:,2]-(x[:,:2]@c-.5330154)
s=s[(h(s)>.38)&~((s[:,0]<-63)&(h(s)<1.45))];tree=cKDTree(s)
for ob in [1,2,3,4,5,8]:
 x=p[(o>=ob)&(h(p)>.38)&~((p[:,0]<-63)&(h(p)<1.45))];d=tree.query(x,workers=-1)[0];x=x[d<.12]
 print(ob,len(x),x.mean(0))
PY"
```

## cmd 33 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree
z=np.load('persistent_candidates.npz');p=z['points'];o=z['observations'];s=np.load('sample_clusters.npz');s=s['points'][s['labels']==0];c=np.array([.00203358,-.01025332]);h=lambda x:x[:,2]-(x[:,:2]@c-.5330154);s=s[(h(s)>.38)&~((s[:,0]<-63)&(h(s)<1.45))];x=p[(o>=2)&(h(p)>.38)&~((p[:,0]<-63)&(h(p)<1.45))];d=cKDTree(s).query(x,workers=-1)[0]
for lim in [.08,.1,.12]:
 y=x[d<lim];sd=cKDTree(y).query(s,workers=-1)[0];fill=s[sd>.12]
 print(lim,len(y),len(fill),'centroids',y.mean(0),np.vstack([y,fill]).mean(0))
PY"
```

## cmd 34 (exit 0)
```
'python3 work_reconstruct.py finalize'
```

## cmd 35 (exit 0)
```
"python3 - <<'PY'
import numpy as np,re
from scipy.spatial import cKDTree
p=np.load('aircraft_points.npy');s=np.load('sample_clusters.npz');s=s['points'][s['labels']==0];c=np.array([.00203358,-.01025332]);h=lambda x:x[:,2]-(x[:,:2]@c-.5330154);s=s[(h(s)>.38)&~((s[:,0]<-63)&(h(s)<1.45))]
for name,x in [('final',p),('sample',s)]:
 w,v=np.linalg.eigh(np.cov(x[:,:2].T));u=v[:,w.argmax()];print(name,len(x),'centroid',x.mean(0),'heading',np.degrees(np.arctan2(u[1],u[0])))
print('centroid delta',np.linalg.norm(p.mean(0)-s.mean(0)))
rng=np.random.default_rng(9);q=p[rng.choice(len(p),30000,False)];d,ix=cKDTree(p).query(q,k=20,workers=-1);x=p[ix]-p[ix].mean(1,keepdims=True);ev=np.linalg.eigvalsh(np.ei
```

## cmd 36 (exit 0)
```
"python3 - <<'PY'
import numpy as np
from scipy.spatial import cKDTree
z=np.load('persistent_candidates.npz');p=z['points'];s=np.load('sample_clusters.npz');s=s['points'][s['labels']==0];c=np.array([.00203358,-.01025332]);h=lambda x:x[:,2]-(x[:,:2]@c-.5330154);s=s[(h(s)>.38)&~((s[:,0]<-63)&(h(s)<1.45))];m=(h(p)>.38)&~((p[:,0]<-63)&(h(p)<1.45));p=p[m];p=p[cKDTree(s).query(p,workers=-1)[0]<.1];f=np.load('aircraft_points.npy')
print('all stationary candidate',len(p),p.mean(0),'final delta',np.linalg.norm(p.mean(0)-f.mean(0)))
for x in [p,f]:
 w,v=np.linalg.eigh(np.cov(x[:,:2].T));u=v[:,w.argmax()];print(np.degrees(np.arctan2(u[1],u[0])))
PY"
```

## message
Completed and validated:

- [trajectory.tum](/app/trajectory.tum) — 1,462/1,462 timestamps, normalized quaternions.
- [aircraft.ply](/app/aircraft.ply) — binary little-endian PLY, 547,880 aircraft-only vertices, apron removed.

