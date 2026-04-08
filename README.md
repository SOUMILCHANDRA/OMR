# 📝 AutoGraderPro — OMR Evaluation System

AutoGraderPro is an automated Optical Mark Recognition (OMR) system designed to evaluate multiple-choice answer sheets from scanned images.

---

## 🚀 Problem

Manual checking of OMR sheets is time-consuming, error-prone, and inefficient for large-scale examinations.

---

## 💡 Solution

This system uses **computer vision techniques** to detect marked answers from scanned sheets and automatically evaluate them against an answer key.

---

## 🧠 Key Features

* 📄 OMR sheet detection from images
* 🎯 Bubble recognition and answer extraction
* ⚡ Automatic scoring system
* 📊 Result generation

---

## ⚙️ How It Works

1. Input image of OMR sheet
2. Image preprocessing (grayscale, thresholding)
3. Contour detection to locate answer regions
4. Bubble detection and marking analysis
5. Comparison with answer key
6. Score calculation

---

## 🏗️ Tech Stack

* **Language:** Python
* **Libraries:** OpenCV, NumPy
* **Image Processing:** Thresholding, contour detection

---

## 📊 Output

* Detected answers
* Final score
* Visual marking of correct/incorrect responses

---

## ⚠️ Challenges

* Handling different lighting conditions
* Aligning skewed or rotated sheets
* Noise in scanned images

---

## 🔮 Future Improvements

* Support for multiple OMR formats
* Batch processing system
* Integration with web interface
* AI-based error correction

---

## 📦 Installation

```bash id="z0r9w9"
git clone https://github.com/SOUMILCHANDRA/OMR
cd OMR
pip install -r requirements.txt
python main.py
```

---

## 👤 Author

Soumil Chandra
Full Stack & Data Visualization Engineer
