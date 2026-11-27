/**
 * StoryForge canonical humanoid pose v1.
 * Coordinates are metres in calibrated actor-local space (Y up).
 * Tracked joints retain their source; inferred joints are explicitly marked.
 */
export type Vec3 = { x: number; y: number; z: number };
export type CanonicalJointName =
  | "pelvis" | "spine" | "chest" | "neck" | "head"
  | "left_shoulder" | "left_elbow" | "left_wrist" | "left_hand"
  | "right_shoulder" | "right_elbow" | "right_wrist" | "right_hand"
  | "left_hip" | "left_knee" | "left_ankle" | "left_foot"
  | "right_hip" | "right_knee" | "right_ankle" | "right_foot";
export type CanonicalSkeleton = {
  format: "storyforge.humanoid";
  version: 1;
  coordinate_space: "actor-local-meters";
  joints: Partial<Record<CanonicalJointName, Vec3>>;
  tracked: CanonicalJointName[];
  inferred: CanonicalJointName[];
};
const add=(a:Vec3,b:Vec3):Vec3=>({x:a.x+b.x,y:a.y+b.y,z:a.z+b.z});
const sub=(a:Vec3,b:Vec3):Vec3=>({x:a.x-b.x,y:a.y-b.y,z:a.z-b.z});
const scale=(a:Vec3,s:number):Vec3=>({x:a.x*s,y:a.y*s,z:a.z*s});
const length=(a:Vec3)=>Math.hypot(a.x,a.y,a.z);
const normalize=(a:Vec3):Vec3=>{const n=length(a)||1;return scale(a,1/n);};
const lerp=(a:Vec3,b:Vec3,t:number):Vec3=>add(a,scale(sub(b,a),t));
function twoBone(start:Vec3,end:Vec3,upper:number,lower:number,pole:Vec3):Vec3 {
  const delta=sub(end,start), distance=Math.max(0.001,Math.min(length(delta),upper+lower-0.001));
  const axis=normalize(delta), along=(upper*upper-lower*lower+distance*distance)/(2*distance);
  const height=Math.sqrt(Math.max(0,upper*upper-along*along));
  let perpendicular=sub(pole,scale(axis,pole.x*axis.x+pole.y*axis.y+pole.z*axis.z));
  if(length(perpendicular)<0.001) perpendicular={x:0,y:0,z:1};
  return add(add(start,scale(axis,along)),scale(normalize(perpendicular),height));
}
export function reconstructCanonicalSkeleton(head:Vec3|null,leftWrist:Vec3|null,rightWrist:Vec3|null):CanonicalSkeleton {
  const h=head??{x:0,y:1.68,z:0};
  const pelvis={x:h.x,y:h.y-0.91,z:h.z};
  const chest=lerp(pelvis,h,0.67), spine=lerp(pelvis,chest,0.55), neck=lerp(chest,h,0.68);
  const ls={x:chest.x-0.23,y:chest.y+0.10,z:chest.z}, rs={x:chest.x+0.23,y:chest.y+0.10,z:chest.z};
  const lw=leftWrist??{x:ls.x-0.27,y:ls.y-0.22,z:ls.z+0.04};
  const rw=rightWrist??{x:rs.x+0.27,y:rs.y-0.22,z:rs.z+0.04};
  const le=twoBone(ls,lw,0.31,0.29,{x:-0.2,y:0.1,z:1});
  const re=twoBone(rs,rw,0.31,0.29,{x:0.2,y:0.1,z:1});
  const lh={x:pelvis.x-0.12,y:pelvis.y,z:pelvis.z}, rh={x:pelvis.x+0.12,y:pelvis.y,z:pelvis.z};
  const la={x:lh.x,y:0.10,z:pelvis.z}, ra={x:rh.x,y:0.10,z:pelvis.z};
  const lk=twoBone(lh,la,0.43,0.43,{x:-0.1,y:0,z:1});
  const rk=twoBone(rh,ra,0.43,0.43,{x:0.1,y:0,z:1});
  const joints:CanonicalSkeleton["joints"]={
    pelvis,spine,chest,neck,head:h,
    left_shoulder:ls,left_elbow:le,left_wrist:lw,left_hand:lw,
    right_shoulder:rs,right_elbow:re,right_wrist:rw,right_hand:rw,
    left_hip:lh,left_knee:lk,left_ankle:la,left_foot:{x:la.x,y:0.04,z:la.z+0.12},
    right_hip:rh,right_knee:rk,right_ankle:ra,right_foot:{x:ra.x,y:0.04,z:ra.z+0.12},
  };
  const tracked:CanonicalJointName[]=[];
  if(head) tracked.push("head");
  if(leftWrist) tracked.push("left_wrist","left_hand");
  if(rightWrist) tracked.push("right_wrist","right_hand");
  const inferred=(Object.keys(joints) as CanonicalJointName[]).filter(name=>!tracked.includes(name));
  return {format:"storyforge.humanoid",version:1,coordinate_space:"actor-local-meters",joints,tracked,inferred};
}
