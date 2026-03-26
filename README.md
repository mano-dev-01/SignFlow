![Team SignFlow](Docs/teamphoto.png)

## TEAM SIGN FLOW
**PyExpo 2026 | PY072 | KGISL Institute of Technology**
**Powered by IPS Tech Community**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Landmarks-00897B?style=for-the-badge)
![PyTorch](https://img.shields.io/badge/PyTorch-Transformer-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20App-000000?style=for-the-badge&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)

---

## SIGNFLOW — Real-Time ASL Recognition & Captioning System

SignFlow is an AI-powered system designed to bridge the communication gap for the Deaf and Hard-of-Hearing community through real-time sign language translation.

> **"Sign language accessibility — everywhere, in real time."**

---

## 📋 Project Details

| Field | Details |
|-------|---------|
| **Team Name** | SIGNFLOW |
| **Problem Statement ID** | PY072 |
| **Problem Statement Title** | ASL TO ENGLISH |
| **Domain** | AIML |
| **PS Category** | Software |

---

## 👥 Team Members

| S.No | Name | Department | Roll No | Role |
|------|------|------------|---------|------|
| 1 | **Mano R P** | CYS | 25UCY127 | Overlay Engineer & Core Developer |
| 2 | **Nithin G** | CYS | 25UCY131 | ML Engineer & Model Architect |
| 3 | **Amritha N** | CSE | 25UCS107 | Research & Development Engineer |
| 4 | **Hari Varna V S** | CYS | 25UCY115 |UI&UX , Digital Media & Content Strategist|
| 5 | **Paul Raja I** | AIDS | 25UAD121 | System Architect & Integration Engineer |
| 6 | **Nithish A** | AIML | 25UAM212 |  Dataset & Data Pipeline Engineer |

---

## 📌 Problem Statement

Communication barriers between sign language users and non-signers create challenges in:

- **Healthcare**
- **Education**
- **Public services**
- **Daily interactions**

**Challenges Addressed:**
- Lack of real-time interpreters
- Limited accessibility tools
- Difficulty in understanding sign grammar
- Communication delays

---

## 💡 Proposed Solution

An AI-based real-time translation system that:

- Detects hand gestures using computer vision
- Converts signs into readable text
- Enhances sentences using LLM-based grammar correction
- Converts text into speech output
- Displays captions through an overlay system

**Innovation:**
- Bi-directional translation
- Web-based and scalable
- Supports regional sign languages

---

## 🌟 Key Features

- Real-time ASL recognition at **30+ FPS**
- Transformer-based deep learning model with **~95% accuracy**
- Always-on-top overlay caption system
- LLM-powered grammar correction and prediction
- Text-to-speech output
- Flask-based web interface
- Scalable for multi-language support

---

## 🏗️ System Architecture
```
Camera / Screen Input
        ↓
MediaPipe (Hand Landmarks)
        ↓
Transformer Model (PyTorch)
        ↓
Text Output
        ↓
LLM Grammar Correction
        ↓
Speech Output (Optional)
        ↓
Overlay Display (PyQt5)
```

---

## 🧠 Model Details

| Specification | Value |
|---------------|-------|
| **Model Type** | Transformer (Landmark-based) |
| **Accuracy** | ~95% |
| **Classes** | 58 ASL Signs |
| **Parameters** | 26.4M |
| **Inference Speed** | 30+ FPS |
| **Hardware** | GPU (CUDA) + CPU |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | PyQt5 |
| **Backend** | Python, Flask |
| **AI/ML** | PyTorch, Transformer |
| **Computer Vision** | OpenCV, MediaPipe |
| **LLM** | Ollama / Google Gemini |
| **Dataset** | MS-ASL, WLASL |

---

## 📊 Applications

- **Healthcare** communication
- **Classroom** accessibility
- **Public service** interaction
- **Everyday** conversations

---

## 📁 Project Structure
```
PY26072/
│
├── 📁 Code/
│   ├── 📁 Model/
│   │   ├── sign_inference.py        # Main inference script
│   │   ├── server.py                # Model API server
│   │   ├── llm_helper.py            # LLM grammar correction
│   │   ├── train_model.py           # Training script
│   │   ├── 📁 models/               # Saved model weights
│   │   ├── 📁 mediapipe_models/     # MediaPipe config files
│   │   └── requirements.txt         # Model dependencies
│   │
│   ├── 📁 SignFlow-Core/
│   │   ├── overlay.py               # Main overlay launcher
│   │   ├── overlay_window.py        # Overlay UI window
│   │   ├── overlay_capture.py       # Screen/webcam capture
│   │   ├── overlay_hand_tracking.py # Hand tracking module
│   │   ├── overlay_voice.py         # Voice-to-text module
│   │   ├── 📁 models/               # Local model files
│   │   ├── 📁 misc/                 # Assets and config
│   │   └── requirements.txt         # Overlay dependencies
│   │
│   └── 📁 SignFlow_Landing_Page/
│       ├── main.py                  # Flask app entry point
│       ├── 📁 templates/            # HTML templates
│       ├── 📁 static/               # CSS, JS, images
│       └── requirements.txt         # Web app dependencies
│
├── 📁 Docs/
│   ├── SignFlow_SOP.pdf             # Standard Operating Procedure
│   ├── teamphoto.png                # Team photo
│   └── Signflow(demo).mp4           # Demo video
│
└── run_signflow.bat                 # One-click launcher
```

---

## ⚙️ Installation & Setup

**1. Clone Repository**
```bash
git clone https://github.com/PyExpo2K26/PY26072.git
cd PY26072
```

**2. Create Virtual Environment**
```bash
python -m venv venv
```

**3. Activate Environment**
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**4. Install Dependencies**
```bash
pip install -r requirements.txt
```

---

## 🚀 Run the Project

**One-Click Launch**
```bash
run_signflow.bat
```

**Run Model**
```bash
cd Code/Model
python sign_inference.py --llm local
```

**Run Overlay App**
```bash
cd Code/SignFlow-Core
python overlay.py
```

**Run Web App**
```bash
cd Code/SignFlow_Landing_Page
python main.py
# Open: http://localhost:5000
```

---

## 🔮 Future Enhancements

- Support for **regional sign languages** (ISL, etc.)
- **Mobile live networking** and streaming support
- **Larger vocabulary** (1000+ signs)
- **Full real-time** conversation system

---

## 📄 Documentation

<table>
<tr>
<td align="center">
<a href="Docs/SignFlow_SOP%20_PY072.pdf">
<img src="https://img.shields.io/badge/-📋%20SOP%20Document-navy?style=for-the-badge&logoColor=white" />
<br/>Standard Operating Procedure
</a>
</td>
<td align="center">
<a href="Docs/Signflow(%20demo).mp4">
<img src="https://img.shields.io/badge/-🎬%20Demo%20Video-darkred?style=for-the-badge&logoColor=white" />
<br/>Watch Demo
</a>
</td>
<td align="center">
<a href="Docs/Team%20Name%20-%20SIGNFLOW%20Problem%20Statement%20ID%20-%20PY072%20Problem%20Statement%20Title%20-%20ASL%20TO%20ENGLISH%20Domain-%20AIML%20PS%20Category-%20Software%20Industry%20Mentor%20-%20Student%20Mentor%20-.pdf">
<img src="https://img.shields.io/badge/-📊%20Presentation-darkorange?style=for-the-badge&logoColor=white" />
<br/>View Slides
</a>
</td>
</tr>
</table>

---

## 🌐 Connect With Us

<table>
<tr>
<td align="center">
<a href="https://www.instagram.com/signflow_pyexpo">
<img src="https://img.shields.io/badge/-Follow%20Us%20on%20Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" />
<br/>@signflow_pyexpo
</a>
</td>
<td align="center">
<a href="https://github.com/PyExpo2K26/PY26072">
<img src="https://img.shields.io/badge/-View%20on%20GitHub-181717?style=for-the-badge&logo=github&logoColor=white" />
<br/>PyExpo2K26 / PY26072
</a>
</td>
</tr>
</table>

---

**Developed by Team SignFlow | PyExpo 2026 | KGISL Institute of Technology**
