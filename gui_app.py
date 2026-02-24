
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import threading
import os
import json
from omr_main import OMRSystem

# Modern Colors
BG_COLOR = "#1E1E1E"        # Dark Gray Background
SIDEBAR_COLOR = "#252526"   # Slightly lighter for containers
ACCENT_COLOR = "#007ACC"    # VS Code Blue
TEXT_COLOR = "#FFFFFF"      # White
TEXT_SECONDARY = "#CCCCCC"  # Light Gray
SUCCESS_COLOR = "#4EC9B0"   # Light Green
ERROR_COLOR = "#F44747"     # Red
BUTTON_HOVER = "#0098FF"

class ModernButton(tk.Button):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.default_bg = kwargs.get('bg', ACCENT_COLOR)
        self.configure(
            relief='flat', 
            activebackground=BUTTON_HOVER, 
            activeforeground='white',
            cursor='hand2',
            bd=0,
            font=("Segoe UI", 11, "bold"),
            fg='white',
            padx=15,
            pady=8
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['bg'] = BUTTON_HOVER

    def on_leave(self, e):
        self['bg'] = self.default_bg

class AISchoolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Teacher Assistant")
        self.root.geometry("900x650")
        self.root.configure(bg=BG_COLOR)
        
        # OMR System Instance
        self.omr = OMRSystem()
        
        # --- UI LAYOUT ---
        
        # 1. Header
        header_frame = tk.Frame(root, bg=SIDEBAR_COLOR, height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        title = tk.Label(header_frame, text="🎓 AI Teacher Assistant", font=("Segoe UI", 18, "bold"), bg=SIDEBAR_COLOR, fg=TEXT_COLOR)
        title.pack(side=tk.LEFT, padx=20, pady=10)
        
        # 2. Main Container
        main_container = tk.Frame(root, bg=BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left Panel (Controls)
        left_panel = tk.Frame(main_container, bg=BG_COLOR, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        # OMR Card
        self.create_card(left_panel, "OMR Scanner", "📝", 
                         "Scan student answer sheets\nand grade them instantly.", 
                         "Scan Sheet", self.run_omr)
        
        # Answer Key Edit Button
        tk.Button(left_panel, text="✏️ Edit Answer Key", command=self.edit_key, 
                  bg=SIDEBAR_COLOR, fg=ACCENT_COLOR, relief="flat", cursor="hand2", 
                  font=("Segoe UI", 10)).pack(pady=5)
        
        tk.Frame(left_panel, height=20, bg=BG_COLOR).pack() # Spacer
        
        # Voice Card
        self.create_card(left_panel, "Voice Coach", "🎤", 
                         "Analyze speech pacing,\ntone, and fluency.", 
                         "Analyze Audio", self.run_voice)
        
        # Right Panel (Output)
        right_panel = tk.Frame(main_container, bg=SIDEBAR_COLOR)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Output Header
        out_header = tk.Label(right_panel, text="Analysis Results", font=("Segoe UI", 12, "bold"), bg=SIDEBAR_COLOR, fg=TEXT_SECONDARY)
        out_header.pack(anchor="w", padx=15, pady=10)
        
        # Console/Log Area
        self.output_area = scrolledtext.ScrolledText(right_panel, width=60, height=20, 
                                                   font=("Consolas", 10), 
                                                   bg="#1E1E1E", fg=TEXT_COLOR, 
                                                   insertbackground="white", relief="flat", padx=10, pady=10)
        self.output_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Configure Tags for coloring
        self.output_area.tag_config('success', foreground=SUCCESS_COLOR)
        self.output_area.tag_config('error', foreground=ERROR_COLOR)
        self.output_area.tag_config('info', foreground=ACCENT_COLOR)
        self.output_area.tag_config('header', font=("Consolas", 11, "bold"), foreground="white")

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(root, textvariable=self.status_var, bg=SIDEBAR_COLOR, fg=TEXT_SECONDARY, font=("Segoe UI", 9), anchor="w", padx=10, pady=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_card(self, parent, title, icon, desc, btn_text, command):
        card = tk.Frame(parent, bg=SIDEBAR_COLOR, padx=20, pady=20)
        card.pack(fill=tk.X)
        
        tk.Label(card, text=icon, font=("Segoe UI", 24), bg=SIDEBAR_COLOR, fg=ACCENT_COLOR).pack(anchor="w")
        tk.Label(card, text=title, font=("Segoe UI", 14, "bold"), bg=SIDEBAR_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(5,0))
        tk.Label(card, text=desc, font=("Segoe UI", 9), bg=SIDEBAR_COLOR, fg=TEXT_SECONDARY, justify="left").pack(anchor="w", pady=(5,15))
        
        btn = ModernButton(card, text=btn_text, command=command, bg=ACCENT_COLOR)
        btn.pack(fill=tk.X)

    def log(self, message, tag=None):
        self.output_area.insert(tk.END, message + "\n", tag)
        self.output_area.see(tk.END)

    def run_omr(self):
        file_path = filedialog.askopenfilename(title="Select OMR Sheet", filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if not file_path:
            return
        
        self.status_var.set(f"Processing {os.path.basename(file_path)}...")
        self.log(f"\n--- Starting OMR Analysis ---", "header")
        self.log(f"File: {os.path.basename(file_path)}")
        
        threading.Thread(target=self._process_omr, args=(file_path,), daemon=True).start()

    def _process_omr(self, file_path):
        try:
            result = self.omr.process_image(file_path, os.path.basename(file_path))
            
            if result:
                q_count = len(result.get('questions', []))
                score = result.get('score', 0)
                correct = result.get('total_correct', 0)
                wrong = result.get('total_wrong', 0)
                
                self.root.after(0, self.log, f"✅ Processing Complete!", "success")
                self.root.after(0, self.log, f"Candidate: {result.get('candidate_name', 'Unknown')}")
                self.root.after(0, self.log, f"Roll No: {result.get('roll_number', 'Not Found')}")
                
                self.root.after(0, self.log, f"\n📊 Results:", "header")
                self.root.after(0, self.log, f"   • Score: {score} / 90", "success" if score > 30 else "error")
                self.root.after(0, self.log, f"   • Correct: {correct} ✅")
                self.root.after(0, self.log, f"   • Wrong: {wrong} ❌")
                self.root.after(0, self.log, f"   • Unanswered: {result.get('unanswered', 0)} ⚪")
                
                self.root.after(0, self.log, "------------------------------------------------")
                self.root.after(0, self.status_var.set, "OMR Analysis Finished")
            else:
                self.root.after(0, self.log, "❌ Error: Could not process image.", "error")
                self.root.after(0, self.status_var.set, "Error")
                
        except Exception as e:
            self.root.after(0, self.log, f"❌ Critical Error: {str(e)}", "error")
            self.root.after(0, self.status_var.set, "Critical Error")

    def edit_key(self):
        key_path = "answer_key.json"
        
        # Create default if missing
        if not os.path.exists(key_path):
             dummy_key = {str(q): 1 for q in range(1, 91)} 
             with open(key_path, 'w') as f:
                 json.dump(dummy_key, f, indent=4)
        
        self.log(f"Opening {key_path} for editing...", "info")
        try:
            os.startfile(key_path) # Windows only
        except Exception as e:
            self.log(f"❌ Could not open editor: {e}", "error")

    def run_voice(self):
        # Add external project to path
        import sys
        external_src = r"d:/audiodetection/src"
        if external_src not in sys.path:
            sys.path.append(external_src)
            
        # Add FFmpeg to PATH
        ffmpeg_path = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
        if os.path.exists(ffmpeg_path):
            os.environ["PATH"] += os.pathsep + ffmpeg_path

        try:
            from audio_processor import AudioProcessor
            from transcriber import Transcriber
            from analyzer import AcousticAnalyzer, TextAnalyzer
        except ImportError as e:
            self.log(f"❌ Import Error: {e}", "error")
            messagebox.showerror("Import Error", f"Could not load modules:\n{e}")
            return

        file_path = filedialog.askopenfilename(title="Select Audio File", filetypes=[("Audio", "*.wav *.mp3 *.m4a *.flac *.mp4")])
        if not file_path:
            return
            
        self.status_var.set(f"Analyzing Audio...")
        self.log(f"\n--- Starting Advance Voice Analysis ---", "header")
        self.log(f"File: {os.path.basename(file_path)}")
        self.log("⏳ Pipeline: Convert -> Transcribe -> Analyze...", "info")
        
        threading.Thread(target=self._process_voice_external, args=(file_path, AudioProcessor, Transcriber, AcousticAnalyzer, TextAnalyzer), daemon=True).start()

    def _process_voice_external(self, file_path, AudioProcessor, Transcriber, AcousticAnalyzer, TextAnalyzer):
        try:
            # 1. Preprocessing
            processor = AudioProcessor()
            try:
                wav_path = processor.convert_to_wav(file_path)
            except Exception as e:
                self.root.after(0, self.log, f"❌ Conversion Error: {str(e)}", "error")
                return
            
            # 2. Transcription
            self.root.after(0, self.status_var.set, "Transcribing...")
            transcriber = Transcriber(model_size="base")
            transcript_data = transcriber.transcribe(wav_path)
            
            # 3. Analysis
            self.root.after(0, self.status_var.set, "Analyzing Acoustics...")
            y, sr = processor.load_audio_librosa(wav_path)
            acoustic_analyzer = AcousticAnalyzer()
            acoustic_metrics = acoustic_analyzer.analyze(y, sr)
            
            self.root.after(0, self.status_var.set, "Analyzing Text...")
            text_analyzer = TextAnalyzer()
            text_metrics = text_analyzer.analyze(transcript_data)
            
            # Display Results
            self.root.after(0, self.log, f"✅ Analysis Complete!", "success")
            self.root.after(0, self.log, f"\n📝 Transcription:")
            self.root.after(0, self.log, f"\"{transcript_data['text']}\"\n")
            
            self.root.after(0, self.log, f"📊 Voice Metrics:")
            self.root.after(0, self.log, f"   • Duration: {acoustic_metrics['duration_sec']:.2f}s")
            self.root.after(0, self.log, f"   • Word Count: {text_metrics['word_count']}")
            self.root.after(0, self.log, f"   • WPM: {text_metrics['wpm']:.1f} (Target: 100-160)", "info")
            self.root.after(0, self.log, f"   • Pauses: {acoustic_metrics['pause_fraction']*100:.1f}%")
            self.root.after(0, self.log, f"   • Pitch Variation: {acoustic_metrics['pitch_std_hz']:.1f} Hz")
            
            self.root.after(0, self.log, f"\n💡 Coach Feedback:", "header")
            
            wpm = text_metrics['wpm']
            if wpm < 100:
                self.root.after(0, self.log, "   ⚠️ Pace is slow. Try to speak more fluently.", "error")
            elif wpm > 160:
                self.root.after(0, self.log, "   ⚠️ Pace is very fast. Slow down.", "error")
            else:
                self.root.after(0, self.log, "   ✅ Good speaking pace.", "success")
                
            pitch_std = acoustic_metrics['pitch_std_hz']
            if pitch_std < 20: 
                 self.root.after(0, self.log, "   ⚠️ Monotone detected. Vary your pitch.", "error")
            else:
                 self.root.after(0, self.log, "   ✅ Expressive tone.", "success")
                 
            self.root.after(0, self.log, "------------------------------------------------")
            self.root.after(0, self.status_var.set, "Voice Analysis Finished")
            
        except Exception as e:
            self.root.after(0, self.log, f"❌ Analysis Error: {str(e)}", "error")
            self.root.after(0, self.status_var.set, "Analysis Error")

if __name__ == "__main__":
    root = tk.Tk()
    app = AISchoolApp(root)
    root.mainloop()
