"""Crop verifier keyframes (base_link) to the aircraft region using ground-truth poses.
Uses spike-1 lidarslam trajectory + the transform that aligns the spike-1 extracted
aircraft onto the reference. Output keeps ORIGINAL base_link coordinates; no poses stored."""
import sys, json, numpy as np
sys.path.insert(0,'tasks/aircraft-orbit-mapping/tests'); import verify_lib as V
MARGIN_XY, MARGIN_Z = float(sys.argv[1]) if len(sys.argv)>1 else 2.5, 1.5
ref=V.load_ply('tasks/aircraft-orbit-mapping/tests/reference/aircraft_ref.ply')
kf=V.load_keyframes('scratch/data/keyframes.npz')
tr=V.load_tum('scratch/spike1/trajectory.tum')
ac=V.load_ply('scratch/oracle_check/aircraft_spike1.ply')
al=V.robust_align(ac,ref); T_ref_w=al.transform; print('aircraft->ref fitness',round(al.fitness,3))
poses=V.interpolate_poses(tr,kf.stamps,0.05)
lo=ref.min(0)-[MARGIN_XY,MARGIN_XY,0.5]; hi=ref.max(0)+[MARGIN_XY,MARGIN_XY,MARGIN_Z]
out={'stamps':kf.stamps,'frame_id':'base_link','ground_z':np.load('scratch/data/keyframes.npz')['ground_z'],
     'crop_note':'points within reference aircraft bbox expanded by %.1f m xy / %.1f m z, coordinates unchanged (base_link)'%(MARGIN_XY,MARGIN_Z)}
counts=[]
for i,(P,pts) in enumerate(zip(poses,kf.points)):
    w=V.transform_points(T_ref_w@P,pts); m=np.all((w>lo)&(w<hi),1)
    out[f'points_{i}']=pts[m].astype(np.float32); counts.append(int(m.sum()))
np.savez_compressed('scratch/data/keyframes_crop.npz',**out)
c=np.array(counts); print('kept per frame min/med/max',c.min(),int(np.median(c)),c.max(),'total',c.sum(),'of',sum(len(p) for p in kf.points))
import os; print('size MB',round(os.path.getsize('scratch/data/keyframes_crop.npz')/1e6,1))
