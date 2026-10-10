// Loads MediaPipe Tasks Vision from the locally cached assets (served by the Python app).
let visionModule = null;
let fileset = null;
const cache = {};

async function base() {
  if (!visionModule) {
    visionModule = await import('/assets/tasks-vision/vision_bundle.mjs');
    fileset = await visionModule.FilesetResolver.forVisionTasks('/assets/tasks-vision/wasm');
  }
  return { vision: visionModule, fileset };
}

async function create(kind, factory) {
  if (cache[kind]) return cache[kind];
  const { vision, fileset: fs } = await base();
  for (const delegate of ['GPU', 'CPU']) {
    try {
      cache[kind] = await factory(vision, fs, delegate);
      cache[kind].delegate = delegate;
      return cache[kind];
    } catch (err) {
      if (delegate === 'CPU') throw err;
      console.warn(`${kind}: GPU delegate failed, falling back to CPU`, err);
    }
  }
  return null;
}

export function poseLandmarker() {
  return create('pose', (v, fs, delegate) => v.PoseLandmarker.createFromOptions(fs, {
    baseOptions: { modelAssetPath: '/assets/models/pose_landmarker_full.task', delegate },
    runningMode: 'VIDEO', numPoses: 1,
    minPoseDetectionConfidence: 0.5, minPosePresenceConfidence: 0.5, minTrackingConfidence: 0.5,
  }));
}

export function faceLandmarker() {
  return create('face', (v, fs, delegate) => v.FaceLandmarker.createFromOptions(fs, {
    baseOptions: { modelAssetPath: '/assets/models/face_landmarker.task', delegate },
    runningMode: 'VIDEO', numFaces: 1, outputFaceBlendshapes: true,
  }));
}
