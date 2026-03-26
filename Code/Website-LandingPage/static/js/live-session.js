/**
 * SignFlow Live Session
 * ---------------------
 * Client-side MediaPipe landmark extraction (92 landmarks) with
 * FastAPI prediction server integration and YouTube-style captions.
 *
 * Landmark layout (matches sign_inference.py exactly):
 *   Slot  0–39 : 40 lip landmarks from face mesh
 *   Slot 40–60 : 21 left-hand landmarks
 *   Slot 61–81 : 21 right-hand landmarks
 *   Slot 82–91 : 10 upper-body pose landmarks
 */

/* ================================================================
   Constants
   ================================================================ */

const TOTAL_LANDMARKS = 92;
const FRAME_BUFFER_SIZE = 40;
const SEND_EVERY_N_FRAMES = 3;
const MP_VERSION = "0.10.14";

// Exact lip indices from sign_inference.py LIPS_FACE_IDXS
const LIPS_FACE_IDXS = [
    61, 185, 40, 39, 37, 0, 267, 269, 270, 409,
    291, 146, 91, 181, 84, 17, 314, 405, 321, 375,
    78, 191, 80, 81, 82, 13, 312, 311, 310, 415,
    95, 88, 178, 87, 14, 317, 402, 318, 324, 308,
];

// Pose upper body indices from sign_inference.py POSE_UPPER_IDXS
const POSE_UPPER_IDXS = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25];

// Hand skeleton connections for drawing
const HAND_CONNECTIONS = [
    [0,1],[1,2],[2,3],[3,4],
    [0,5],[5,6],[6,7],[7,8],
    [0,9],[9,10],[10,11],[11,12],
    [0,13],[13,14],[14,15],[15,16],
    [0,17],[17,18],[18,19],[19,20],
    [5,9],[9,13],[13,17],
];

// Lip contour drawing connections
const LIP_OUTER = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,0];
const LIP_INNER = [20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,20];

// Pose skeleton connections
const POSE_CONNECTIONS = [
    [0,1],[0,2],[1,3],[2,4],[3,5],[4,6],[1,7],[2,8],[7,8],[1,2],
];

/* ================================================================
   DOM References
   ================================================================ */

const setupPanel = document.getElementById("live-setup");
const livePage = document.getElementById("live-page");
const setupForm = document.getElementById("setup-form");
const serverUrlInput = document.getElementById("server-url");
const startBtn = document.getElementById("start-btn");
const viewport = document.getElementById("live-viewport");
const loadingOverlay = document.getElementById("live-loading");
const loadingText = document.getElementById("loading-text");
const video = document.getElementById("camera-video");
const canvas = document.getElementById("camera-canvas");
const ctx = canvas.getContext("2d");
const statusDot = document.getElementById("status-dot");
const statusLabel = document.getElementById("status-label");
const fpsBadge = document.getElementById("fps-badge");
const captionPill = document.getElementById("caption-pill");
const captionText = document.getElementById("caption-text");
const captionConfidence = document.getElementById("caption-confidence");
const stopBtn = document.getElementById("stop-btn");
const flipBtn = document.getElementById("flip-btn");
const toastEl = document.getElementById("live-toast");

// Debug panel references
const debugServerStatus = document.getElementById("debug-server-status");
const debugLastRequest = document.getElementById("debug-last-request");
const debugLastResponse = document.getElementById("debug-last-response");
const debugLastError = document.getElementById("debug-last-error");

/* ================================================================
   State
   ================================================================ */

// Default server URL comes from the page config and falls back to the public HF Space.
let serverUrl = (
    (livePage && livePage.dataset ? livePage.dataset.serverUrl : "") ||
    "https://mano-dev-01-signflow-inference.hf.space"
).replace(/\/$/, "");
let faceLandmarker = null;
let handLandmarker = null;
let poseLandmarker = null;
let stream = null;
let animFrameId = null;
let running = false;
let facingMode = "user";
let mediapipeReady = false;
let isFlipping = false;

let frameBuffer = [];
let frameCount = 0;
let pendingRequest = false;

let fpsFrames = 0;
let fpsLastTime = performance.now();

let lastCaption = "";
let captionTimeout = null;

/* ================================================================
   Toast Helper
   ================================================================ */

let toastTimer = null;

function showToast(message, type, duration) {
    type = type || "error";
    duration = duration || 4000;
    console.log("[SignFlow Toast]", type, message);
    toastEl.textContent = message;
    toastEl.className = "live-toast is-visible" + (type !== "error" ? " toast-" + type : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function() {
        toastEl.classList.remove("is-visible");
    }, duration);
}

/* ================================================================
   MediaPipe Initialization
   ================================================================ */

import { FaceLandmarker, HandLandmarker, PoseLandmarker, FilesetResolver } 
    from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs";

async function initMediaPipe() {
    loadingText.textContent = "Preparing AI engine…";

    var vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@" + MP_VERSION + "/wasm"
    );

    loadingText.textContent = "Loading Face Landmarker…";
    faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath:
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
            delegate: "GPU",
        },
        runningMode: "VIDEO",
        numFaces: 1,
        outputFaceBlendshapes: false,
        outputFacialTransformationMatrixes: false,
    });

    loadingText.textContent = "Loading Hand Landmarker…";
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath:
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "GPU",
        },
        runningMode: "VIDEO",
        numHands: 2,
    });

    loadingText.textContent = "Loading Pose Landmarker…";
    poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath:
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
            delegate: "GPU",
        },
        runningMode: "VIDEO",
        numPoses: 1,
    });

    loadingText.textContent = "Models loaded ✓";
}

/* ================================================================
   Camera
   ================================================================ */

async function startCamera() {
    loadingText.textContent = "Requesting camera access…";

    var constraints = {
        video: {
            facingMode: facingMode,
            width: { ideal: 640 },
            height: { ideal: 480 },
        },
        audio: false,
    };

    try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (err) {
        if (err.name === "NotAllowedError") {
            showToast("Camera permission denied. Please allow camera access and reload.");
        } else if (err.name === "NotFoundError") {
            showToast("No camera found on this device.");
        } else {
            showToast("Camera error: " + err.message);
        }
        throw err;
    }

    video.srcObject = stream;
    
    // Explicitly play the video so it doesn't get stuck on mobile
    try {
        await video.play();
    } catch (e) {
        console.warn("Auto-play prevented:", e);
    }

    return new Promise(function(resolve) {
        if (video.readyState >= 2) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            resolve();
        } else {
            video.onloadedmetadata = function() {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                resolve();
            };
        }
    });
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(function(t) { t.stop(); });
        stream = null;
    }
}

/* ================================================================
   92-Landmark Extraction
   ================================================================ */

function extractLandmarks(faceResult, handResult, poseResult) {
    var landmarks = new Array(TOTAL_LANDMARKS);
    for (var i = 0; i < TOTAL_LANDMARKS; i++) {
        landmarks[i] = [0, 0, 0];
    }

    // Slot 0–39: Lip landmarks from face mesh
    if (faceResult.faceLandmarks && faceResult.faceLandmarks.length > 0) {
        var facePts = faceResult.faceLandmarks[0];
        for (var i = 0; i < LIPS_FACE_IDXS.length; i++) {
            var idx = LIPS_FACE_IDXS[i];
            if (idx < facePts.length) {
                landmarks[i] = [facePts[idx].x, facePts[idx].y, facePts[idx].z];
            }
        }
    }

    // Slot 40–60 (left) and 61–81 (right): Hand landmarks
    if (handResult.landmarks && handResult.landmarks.length > 0) {
        var leftHand = null;
        var rightHand = null;

        if (handResult.landmarks.length === 1) {
            var label = handResult.handedness[0][0].categoryName;
            if (label === "Left") {
                leftHand = handResult.landmarks[0];
            } else {
                rightHand = handResult.landmarks[0];
            }
        } else if (handResult.landmarks.length >= 2) {
            var label0 = handResult.handedness[0][0].categoryName;
            var label1 = handResult.handedness[1][0].categoryName;

            if (label0 !== label1) {
                if (label0 === "Left") {
                    leftHand = handResult.landmarks[0];
                    rightHand = handResult.landmarks[1];
                } else {
                    leftHand = handResult.landmarks[1];
                    rightHand = handResult.landmarks[0];
                }
            } else {
                var wrist0X = handResult.landmarks[0][0].x;
                var wrist1X = handResult.landmarks[1][0].x;
                if (wrist0X < wrist1X) {
                    leftHand = handResult.landmarks[0];
                    rightHand = handResult.landmarks[1];
                } else {
                    leftHand = handResult.landmarks[1];
                    rightHand = handResult.landmarks[0];
                }
            }
        }

        if (leftHand) {
            for (var i = 0; i < 21; i++) {
                landmarks[40 + i] = [leftHand[i].x, leftHand[i].y, leftHand[i].z];
            }
        }
        if (rightHand) {
            for (var i = 0; i < 21; i++) {
                landmarks[61 + i] = [rightHand[i].x, rightHand[i].y, rightHand[i].z];
            }
        }
    }

    // Slot 82–91: Pose (upper body)
    if (poseResult.landmarks && poseResult.landmarks.length > 0) {
        var posePts = poseResult.landmarks[0];
        for (var i = 0; i < POSE_UPPER_IDXS.length; i++) {
            var idx = POSE_UPPER_IDXS[i];
            if (idx < posePts.length) {
                landmarks[82 + i] = [posePts[idx].x, posePts[idx].y, posePts[idx].z];
            }
        }
    }

    return landmarks;
}

/* ================================================================
   Landmark Drawing
   ================================================================ */

function drawLandmarks(landmarks, w, h) {
    ctx.clearRect(0, 0, w, h);

    // Lips (cyan)
    if (landmarks[0][0] !== 0 || landmarks[0][1] !== 0) {
        ctx.strokeStyle = "rgba(34, 211, 238, 0.85)";
        ctx.lineWidth = 2;
        drawLoop(landmarks, LIP_OUTER, w, h);
        drawLoop(landmarks, LIP_INNER, w, h);
        drawDots(landmarks, 0, 40, w, h, "rgba(34, 211, 238, 0.7)", 2);
    }

    // Left hand (green)
    drawHand(landmarks, 40, w, h, "rgba(34, 197, 94, 0.85)", "rgba(34, 197, 94, 0.6)");

    // Right hand (blue)
    drawHand(landmarks, 61, w, h, "rgba(96, 165, 250, 0.85)", "rgba(96, 165, 250, 0.6)");

    // Pose (magenta)
    drawPose(landmarks, w, h);
}

function drawLoop(landmarks, indices, w, h) {
    ctx.beginPath();
    for (var i = 0; i < indices.length; i++) {
        var pt = landmarks[indices[i]];
        if (pt[0] === 0 && pt[1] === 0) continue;
        if (i === 0) ctx.moveTo(pt[0] * w, pt[1] * h);
        else ctx.lineTo(pt[0] * w, pt[1] * h);
    }
    ctx.stroke();
}

function drawDots(landmarks, start, count, w, h, color, r) {
    ctx.fillStyle = color;
    for (var i = 0; i < count; i++) {
        var pt = landmarks[start + i];
        if (pt[0] === 0 && pt[1] === 0) continue;
        ctx.beginPath();
        ctx.arc(pt[0] * w, pt[1] * h, r, 0, Math.PI * 2);
        ctx.fill();
    }
}

function drawHand(landmarks, offset, w, h, lineColor, dotColor) {
    if (landmarks[offset][0] === 0 && landmarks[offset][1] === 0) return;
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2.5;
    for (var c = 0; c < HAND_CONNECTIONS.length; c++) {
        var a = HAND_CONNECTIONS[c][0], b = HAND_CONNECTIONS[c][1];
        var ptA = landmarks[offset + a], ptB = landmarks[offset + b];
        if ((ptA[0] === 0 && ptA[1] === 0) || (ptB[0] === 0 && ptB[1] === 0)) continue;
        ctx.beginPath();
        ctx.moveTo(ptA[0] * w, ptA[1] * h);
        ctx.lineTo(ptB[0] * w, ptB[1] * h);
        ctx.stroke();
    }
    drawDots(landmarks, offset, 21, w, h, dotColor, 3.5);
}

function drawPose(landmarks, w, h) {
    if (landmarks[82][0] === 0 && landmarks[82][1] === 0) return;
    ctx.strokeStyle = "rgba(168, 85, 247, 0.7)";
    ctx.lineWidth = 2;
    for (var c = 0; c < POSE_CONNECTIONS.length; c++) {
        var a = POSE_CONNECTIONS[c][0], b = POSE_CONNECTIONS[c][1];
        var ptA = landmarks[82 + a], ptB = landmarks[82 + b];
        if ((ptA[0] === 0 && ptA[1] === 0) || (ptB[0] === 0 && ptB[1] === 0)) continue;
        ctx.beginPath();
        ctx.moveTo(ptA[0] * w, ptA[1] * h);
        ctx.lineTo(ptB[0] * w, ptB[1] * h);
        ctx.stroke();
    }
    drawDots(landmarks, 82, 10, w, h, "rgba(168, 85, 247, 0.6)", 4);
}

/* ================================================================
   API Communication
   ================================================================ */

async function sendToServer(buffer) {
    if (pendingRequest) return;
    pendingRequest = true;

    // Show request info
    if (debugLastRequest) debugLastRequest.textContent = JSON.stringify({frames: buffer}).slice(0, 120) + (buffer.length > 40 ? '...':'');
    if (debugServerStatus) debugServerStatus.textContent = 'Connecting...';
    if (debugLastError) debugLastError.textContent = '-';

    try {
        var response = await fetch(serverUrl + "/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ frames: buffer }),
        });

        if (!response.ok) throw new Error("Server responded " + response.status);

        var data = await response.json();

        // Show response info
        if (debugLastResponse) debugLastResponse.textContent = JSON.stringify(data);
        if (debugServerStatus) debugServerStatus.textContent = 'OK';

        if (data.sign && data.sign !== lastCaption) {
            lastCaption = data.sign;
            captionText.textContent = data.sign;
            captionPill.classList.add("is-visible");

            if (data.confidence !== undefined) {
                captionConfidence.textContent = (data.confidence * 100).toFixed(0) + "% confidence";
            } else {
                captionConfidence.textContent = "";
            }

            clearTimeout(captionTimeout);
            captionTimeout = setTimeout(function() {
                captionPill.classList.remove("is-visible");
            }, 5000);
        }
    } catch (err) {
        console.warn("API error:", err.message);

        // Show error info
        if (debugLastError) debugLastError.textContent = err.message;
        if (debugServerStatus) debugServerStatus.textContent = 'Error';
    } finally {
        pendingRequest = false;
    }
}

/* ================================================================
   Main Processing Loop
   ================================================================ */

function processFrame() {
    if (!running) return;

    var now = performance.now();

    try {
        var faceResult = faceLandmarker.detectForVideo(video, now);
        var handResult = handLandmarker.detectForVideo(video, now);
        var poseResult = poseLandmarker.detectForVideo(video, now);

        var landmarks = extractLandmarks(faceResult, handResult, poseResult);
        drawLandmarks(landmarks, canvas.width, canvas.height);

        frameBuffer.push(landmarks);
        if (frameBuffer.length > FRAME_BUFFER_SIZE) {
            frameBuffer.shift();
        }

        frameCount++;
        if (frameCount % SEND_EVERY_N_FRAMES === 0 && frameBuffer.length >= 5) {
            sendToServer(frameBuffer.slice());
        }
    } catch (err) {
        console.warn("Frame processing error:", err.message);
    }

    // FPS
    fpsFrames++;
    if (now - fpsLastTime >= 1000) {
        fpsBadge.textContent = fpsFrames + " fps";
        fpsFrames = 0;
        fpsLastTime = now;
    }

    animFrameId = requestAnimationFrame(processFrame);
}

/* ================================================================
   Session Lifecycle
   ================================================================ */

async function startSession() {
    running = true;
    frameBuffer = [];
    frameCount = 0;
    pendingRequest = false;
    lastCaption = "";

    setupPanel.classList.add("is-hidden");
    viewport.classList.add("is-active");
    loadingOverlay.classList.add("is-active");

    try {
        await initMediaPipe();
        await startCamera();

        loadingOverlay.classList.remove("is-active");
        
        statusDot.classList.add("is-connected");
        statusLabel.textContent = "Ready";

        showToast("Session started! Show sign language gestures to the camera.", "success", 3000);

        processFrame();
    } catch (err) {
        console.error("Start session error:", err);
        showToast("Failed to start: " + err.message);
        stopSession();
    }
}

function stopSession() {
    running = false;
    if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
    }
    stopCamera();

    viewport.classList.remove("is-active");
    loadingOverlay.classList.remove("is-active");
    setupPanel.classList.remove("is-hidden");
    captionPill.classList.remove("is-visible");
    statusDot.classList.remove("is-connected");
    statusLabel.textContent = "Connecting…";
    fpsBadge.textContent = "-- fps";
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

async function flipCamera() {
    if (isFlipping) return;
    isFlipping = true;

    // 1. Temporarily pause the loop so MediaPipe doesn't process broken empty frames
    let wasRunning = running;
    running = false;
    if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
    }

    // 2. Switch camera stream
    facingMode = facingMode === "user" ? "environment" : "user";
    stopCamera();

    // 3. Visual feedback
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    loadingOverlay.classList.add("is-active");
    loadingText.textContent = "Switching camera…";

    try {
        await startCamera();
        
        // Wait a small moment to ensure video actually has valid frames playing
        await new Promise(r => setTimeout(r, 600));

        loadingOverlay.classList.remove("is-active");

        // 4. Resume loop cleanly
        if (wasRunning) {
            running = true;
            processFrame();
        }
    } catch (e) {
        showToast("Could not switch camera.");
        loadingOverlay.classList.remove("is-active");
    } finally {
        isFlipping = false;
    }
}

/* ================================================================
   Event Listeners
   ================================================================ */


// Update serverUrl from input box before starting session
setupForm.addEventListener("submit", function(e) {
    e.preventDefault();
    if (serverUrlInput && serverUrlInput.value) {
        serverUrl = serverUrlInput.value.trim().replace(/\/$/, "");
    }
    startBtn.disabled = true;
    startBtn.textContent = "Starting…";
    startSession().finally(function() {
        startBtn.disabled = false;
        startBtn.textContent = "Start Session";
    });
});

stopBtn.addEventListener("click", stopSession);
flipBtn.addEventListener("click", flipCamera);

// Initialize any Lucide icons on this page specifically (e.g. the setup icon)
if (window.lucide) {
    window.lucide.createIcons();
}

console.log("[SignFlow] Live session script loaded ✓");


