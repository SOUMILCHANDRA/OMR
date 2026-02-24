# AI Teacher Assistant & OMR Scanner

A modern GUI application that combines an Intelligent OMR (Optical Mark Recognition) Scanner with a Voice Coaching module using OpenAI Whisper.

## 🚀 Features (What it CAN do)
1.  **High-Precision OMR Scanning**:
    *   **90 Questions Support**: Specifically tuned for 5-column, 90-row OMR sheets.
    *   **Global Grid Alignment**: Automatically detects the page structure and fits a master grid to eliminate "row drift" or misalignment.
    *   **Differential Scoring**: Compares bubble darkness against its neighbors to ignore printed borders and detect even faint pencil marks.
    *   **Visual Feedback**: Generates `debug_` images showing **Blue Boxes** (Answer Key) vs. **Green/Red Boxes** (Student Detection).
2.  **Automated Grading**:
    *   Loads `answer_key.json` to calculate scores instantly.
    *   Calculates Score, Correct, Wrong, and Unanswered counts.
3.  **Voice Coach**:
    *   Transcribes audio lessons/recordings using OpenAI Whisper.
    *   Analyzes pace (Words Per Minute).
    *   Detects filler words (um, uh) to help teachers improve their delivery.
4.  **Modern Dark GUI**:
    *   Industrial dark theme with a terminal-style log for real-time processing feedback.
    *   Integrated card-based navigation.

## ⚠️ Limitations (What it CAN'T do Yet)
1.  **Non-Standard Layouts**: Currently hardcoded for a specific 5-column / 18-row-per-column (90 questions) sheet layout.
2.  **Severe Distortion**: While it handles minor skews, extremely crumpled or heavily rotated (e.g., upside down) sheets might fail detection.
3.  **Handwriting Recognition**: It extracts the Candidate Name/Roll No using OCR, but performance varies based on text clarity (it does not read cursive well).
4.  **Multiple Marks**: If a student bubbles two options for one question, it currently picks the darkest one but doesn't flag it as "Multi-marked" invalid (future update).

## 🛠 Libraries Used
*   `opencv-python`: Image processing and bubble detection.
*   `numpy`: Numerical calculations for grid fitting.
*   `pytesseract`: Tesseract OCR for header text extraction.
*   `imutils`: Image utility functions.
*   `openai-whisper`: AI-powered transcription.
*   `tkinter`: GUI framework.
*   `pydantic` / `json`: Data structuring.

## 📦 Installation
1.  **Install Tesseract OCR**: [Download here](https://github.com/UB-Mannheim/tesseract/wiki/download) and ensure it's at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
2.  **Install FFmpeg**: Required for the Voice Coach (Whisper).
3.  **Python Dependencies**:
    ```bash
    pip install opencv-python numpy pytesseract imutils openai-whisper
    ```

## 📋 How to Use
1.  Run `python gui_app.py`.
2.  Click **"Edit Answer Key"** to set your correct answers.
3.  Click **"Scan Sheet"** to process a student's paper.
4.  Switch to **"Voice Coach"** to analyze audio recordings.
