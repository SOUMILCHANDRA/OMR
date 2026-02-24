
import cv2
import numpy as np
import pytesseract
import json
import imutils
import os
import base64
from collections import defaultdict

class OMRSystem:
    def __init__(self):
        # Configuration
        self.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(self.tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        
    def preprocess_image(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # adaptiveThreshold with C=2 (more sensitive to faint marks)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 2)
        
        # Morphological operations to enhance/connect potentially broken pencil marks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        return gray, thresh

    def find_bubbles(self, thresh, min_w=13, max_w=95, min_h=13, max_h=95): # Relaxed to catch all sizes
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        bubbles = []
        for c in cnts:
            (x, y, w, h) = cv2.boundingRect(c)
            ar = w / float(h)
            if w >= min_w and h >= min_h and w <= max_w and h <= max_h and ar >= 0.5 and ar <= 1.8:
                bubbles.append((x, y, w, h))
        return bubbles

    def group_bubbles_into_columns(self, bubbles):
        # Cluster by X-coordinate
        # Sort by X
        bubbles.sort(key=lambda b: b[0])
        
        columns = []
        if not bubbles:
            return columns
            
        current_col = [bubbles[0]]
        
        # Simple clustering: if center X is close
        for i in range(1, len(bubbles)):
            b = bubbles[i]
            prev_b = current_col[-1]
            
            # Compare center X
            cx = b[0] + b[2]//2
            prev_cx = prev_b[0] + prev_b[2]//2
            
            if abs(cx - prev_cx) < 20: # 20px tolerance for vertical alignment
                current_col.append(b)
            else:
                columns.append(sorted(current_col, key=lambda b: b[1]))
                current_col = [b]
        columns.append(sorted(current_col, key=lambda b: b[1]))
        
        # Filter small columns (noise)
        valid_cols = [c for c in columns if len(c) > 5]
        return valid_cols

    def group_columns_into_blocks(self, columns):
        # Blocks are groups of columns that are physically close (e.g. A, B, C, D)
        # Sort columns by their average X
        col_stats = []
        for col in columns:
            avg_x = sum([b[0] for b in col]) / len(col)
            min_y = min([b[1] for b in col])
            max_y = max([b[1] for b in col])
            col_stats.append({
                'col': col,
                'avg_x': avg_x,
                'y_range': (min_y, max_y),
                'count': len(col)
            })
            
        col_stats.sort(key=lambda x: x['avg_x'])
        
        blocks = []
        if not col_stats:
            return blocks
            
        current_block = [col_stats[0]]
        
        for i in range(1, len(col_stats)):
            curr = col_stats[i]
            prev = current_block[-1]
            
            # Distance check
            dist = curr['avg_x'] - prev['avg_x']
            
            # Also check vertical alignment overlap
            y_overlap = min(curr['y_range'][1], prev['y_range'][1]) - max(curr['y_range'][0], prev['y_range'][0])
            
            # If close enough and vertically aligned
            if dist < 80 and y_overlap > 0: # 80px max separation between option columns
                current_block.append(curr)
            else:
                blocks.append(current_block)
                current_block = [curr]
        blocks.append(current_block)
        
        return blocks

    def analyze_block(self, block, thresh):
        # A block is a list of columns
        # If block has 4 columns -> Likely Question Block (A, B, C, D)
        # If block has 6 or more -> Likely Number Grid (Roll No, UDISE)
        
        num_cols = len(block)
        cols = [item['col'] for item in block]
        
        # Determine Block Type
        block_type = "unknown"
        if 3 <= num_cols <= 6: 
            block_type = "questions"
            # If > 4 columns, we likely picked up the numbering column on the left (1, 2, 3...)
            # Assume options A, B, C, D are the right-most 4 columns
            if num_cols > 4:
                cols = cols[-4:]
                
        elif num_cols >= 7: # Strict threshold for grid
            block_type = "grid_field" # e.g. Roll No logic
            
        return block_type, cols
        
    def extract_answers_from_question_block(self, cols, thresh):
        # Assume columns are options A, B, C, D...
        # We need to align them row by row across columns
        # Collect all bubbles from all columns
        all_bubbles = []
        for c_idx, col in enumerate(cols):
            for b in col:
                all_bubbles.append((b, c_idx)) # Keep track of which option index (0=A, 1=B...)
                
        # Sort by Y
        all_bubbles.sort(key=lambda x: x[0][1])
        
        # Group into rows
        rows = []
        if not all_bubbles:
            return []
            
        curr_row = [all_bubbles[0]]
        for i in range(1, len(all_bubbles)):
            b_data = all_bubbles[i]
            prev_b_data = curr_row[-1]
            
            # Compare Y center
            cy = b_data[0][1] + b_data[0][3]//2
            prev_cy = prev_b_data[0][1] + prev_b_data[0][3]//2
            
            if abs(cy - prev_cy) < 15: # Same row
                curr_row.append(b_data)
            else:
                rows.append(curr_row)
                curr_row = [b_data]
        rows.append(curr_row)
        
        results = []
        
        for row in rows:
            # Check filling
            max_fill = 0
            selected_opt = 0 # 0 means none
            
            row_bubbles = [] # list of (opt_idx, fill_ratio)
            
            for (bx, by, bw, bh), opt_idx in row:
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.rectangle(mask, (bx, by), (bx+bw, by+bh), 255, -1)
                mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                total = cv2.countNonZero(mask)
                fill_ratio = total / (bw*bh)
                row_bubbles.append((opt_idx, fill_ratio))
                
                if fill_ratio > 0.45 and total > max_fill:
                    max_fill = total
                    selected_opt = opt_idx + 1 # 1-based index
            
            # Refinement: if multiple bubbled, mark invalid?
            # Or take max. For now simple max.
            
            results.append(selected_opt)
            
        return results

    def extract_digits_from_grid_block(self, cols, thresh):
        # Similar logic but for digits 0-9
        # Assuming columns represent digits positions (100s, 10s, 1s)
        # Assuming rows represent values 0-9
        
        # We process each column independently to find the marked digit
        digits = []
        for col in cols:
            # Sort bubbles in column top-to-bottom (0 to 9)
            col.sort(key=lambda b: b[1])
            
            # We expect ~10 bubbles. 
            # If we find fewer, we might have merged/missed.
            # Best effort: find the most filled one.
            
            best_digit = -1
            max_fill = 0
            
            for i, (bx, by, bw, bh) in enumerate(col):
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.rectangle(mask, (bx, by), (bx+bw, by+bh), 255, -1)
                mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                total = cv2.countNonZero(mask)
                fill_ratio = total / (bw*bh)
                
                if fill_ratio > 0.45 and total > max_fill:
                    max_fill = total
                    # Map index i to digit? 
                    # Usually 0 is top or 1 is top? standard is 0 on top? Or 1..9,0?
                    # Let's assume standard: 0,1,2,3,4,5,6,7,8,9
                    best_digit = i 
            
            if best_digit != -1:
                digits.append(str(best_digit))
            else:
                digits.append("?")
                
        return "".join(digits)

    def extract_header_text(self, gray):
        # ROI: Top 25% of image
        h, w = gray.shape
        # Use the entire provided image for OCR (we crop before calling this)
        roi = gray
        
        # Tesseract configuration
        custom_config = r'--oem 3 --psm 6' # Assume block of text
        
        text_data = {}
        
        # Try different language combos
        try:
             # Look for specific keywords?
             txt = pytesseract.image_to_string(roi, lang='mar+eng', config=custom_config)
             text_data['raw_ocr'] = txt
        except:
             try:
                 txt = pytesseract.image_to_string(roi, lang='eng', config=custom_config)
                 text_data['raw_ocr'] = txt
             except:
                 text_data['raw_ocr'] = ""
        
        # Parse logic (very basic heuristics)
        lines = text_data['raw_ocr'].split('\n')
        name_candidates = [l for l in lines if len(l) > 3 and "Name" in l]
        text_data['candidate_name'] = name_candidates[0] if name_candidates else "Unknown"
        
        return text_data

    def process_image(self, image_path, filename):
        image = cv2.imread(image_path)
        if image is None:
            return None

        # User-defined ROI for Questions (tuned)
        # 765->730 to fully catch top row bubbles (now that min_w=18 filters noise)
        roi_x1, roi_x2 = 70, 1230
        roi_y1, roi_y2 = 730, 1810
        
        # 1. Process Questions in the specific ROI
        # Check bounds
        h, w = image.shape[:2]
        roi_x1 = max(0, roi_x1); roi_x2 = min(w, roi_x2)
        roi_y1 = max(0, roi_y1); roi_y2 = min(h, roi_y2)
        
        question_roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
        
        # Preprocess the ROI
        gray_roi, thresh_roi = self.preprocess_image(question_roi)
        
        # Find bubbles in ROI
        bubbles_local = self.find_bubbles(thresh_roi)
        
        # Convert local ROI coordinates back to global image coordinates
        bubbles = []
        for (bx, by, bw, bh) in bubbles_local:
            bubbles.append((bx + roi_x1, by + roi_y1, bw, bh))
            
        extracted_data = {
            "filename": filename,
            "candidate_name": "",
            "udise_number": "",
            "roll_number": "",
            "questions": []
        }

        # 2. GRID FORCE LOGIC
        # We expect 5 horizontal blocks (columns of questions) and 18 vertical rows per block.
        # Total 90 questions.
        
        # Step A: Cluster Bubbles into 5 Main Blocks based on X-coordinates
        # We need to find the centers of the 5 big columns (Q1-18, Q19-36, etc.)
        
        if not bubbles:
            print(f"[{filename}] No bubbles found in ROI! Checking raw pixel intensity relative to ROI geometric division.")
            return extracted_data

        # We need global threshold for the subsequent grid reading
        _, thresh = self.preprocess_image(image)
        
        # --- NEW: Create a "Clean" threshold for counting to remove bubble borders ---
        # Erosion removes thin lines (borders) but keeps solid blobs (marks)
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh_clean = cv2.erode(thresh, kernel_clean, iterations=1)
        # ---------------------------------------------------------------------------

        bubbles.sort(key=lambda b: b[0]) # Sort by X
        
        # Simple 1D clustering to find Block Centers
        block_x_groups = []
        current_group = [bubbles[0]]
        for i in range(1, len(bubbles)):
            if bubbles[i][0] - bubbles[i-1][0] > 60: # Gap between blocks (big gap > option gap)
                block_x_groups.append(current_group)
                current_group = [bubbles[i]]
            else:
                current_group.append(bubbles[i])
        block_x_groups.append(current_group)
        
        # Start visualization
        vis = image.copy()
        cv2.rectangle(vis, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 0, 0), 2)
        
        # We need exactly 5 blocks. 
        # If found > 5, merge or pick top 5? If < 5, we have a problem (missing entire stack).
        # Let's filter groups that are too small (noise)
        valid_blocks = [g for g in block_x_groups if len(g) > 10]
        
        # Calculate average block spacing (stride)
        block_centers = [ int(sum([b[0] for b in g])/len(g)) for g in valid_blocks ]
        
        avg_stride = 235 # Default guess based on ROI width
        if len(block_centers) > 1:
            # We can calculate stride
            # But wait, we might have merged/missed blocks in between.
            # safe logic: (max - min) / (n_blocks - 1) ??
            # Only if n_blocks seems correct.
            # Best effort: use adjacent differences
            diffs = np.diff(block_centers)
            # Filter huge jumps (missing blocks)
            valid_diffs = [d for d in diffs if 180 < d < 280]
            if valid_diffs:
                avg_stride = np.mean(valid_diffs)
        
        print(f"[{filename}] Using Block Stride: {avg_stride:.1f}")
        
        # Determine anchor X (start of first block)
        # If first block is near left edge (ROI x=70 + margin), use it.
        # Otherwise extrapolate backwards.
        start_x_anchor = 70 + 60 # Rough geometric guess?
        if block_centers:
            # Align anchor to the first found block
            # But which index does the first found block correspond to? 0? 1?
            # ROI x starts at 70. First block usually at ~70+something.
            # Let's assume the left-most *found* block is likely index 0 IF it's close to left edge.
            if block_centers[0] < roi_x1 + 150:
                start_x_anchor = block_centers[0]
            else:
                 # It's likely block 1 or 2...
                 # We need to shift anchor back
                 shift = round((block_centers[0] - (roi_x1 + 60)) / avg_stride)
                 start_x_anchor = block_centers[0] - shift * avg_stride

        # --- GLOBAL ROW DETECTION & ALIGNMENT ---
        # 1. Collect all detected bubble Y-centers
        all_ys = [b[1] + b[3]//2 for b in bubbles]
        all_ys.sort()
        
        # 2. Cluster into distinct rows (Cluster gaps > 20px)
        row_clusters = []
        if all_ys:
            curr = [all_ys[0]]
            for y in all_ys[1:]:
                if y - curr[-1] > 20: 
                    row_clusters.append(int(sum(curr)/len(curr)))
                    curr = [y]
                else:
                    curr.append(y)
            row_clusters.append(int(sum(curr)/len(curr)))
        
        # 3. Fit the Perfect Grid (Y = Start + r * Stride)
        # Standard OMR Stride is approx 58px. Top margin ~45px relative to ROI.
        avg_h = 58.0
        start_y_est = roi_y1 + 45 
        
        if len(row_clusters) > 5:
             # Calculate better stride from data
             diffs = np.diff(row_clusters)
             valid_diffs = [d for d in diffs if 40 < d < 70] # Filter outliers
             if valid_diffs:
                 avg_h = np.median(valid_diffs)

             # Align Start Y to the best fitting cluster
             # We try to match our clusters to the theoretical grid indices 0..17
             best_shift = 0
             min_err = float('inf')
             
             # Search small range +/- 40px to snap the grid
             for shift in range(-40, 41, 2):
                 tentative_start = start_y_est + shift
                 err = 0
                 matches = 0
                 for rc in row_clusters:
                     # Which row index is this cluster?
                     r_idx = round((rc - tentative_start) / avg_h)
                     if 0 <= r_idx < 18:
                         pred_y = tentative_start + r_idx * avg_h
                         err += abs(rc - pred_y)
                         matches += 1
                 
                 if matches > 3:
                     avg_err = err / matches
                     if avg_err < min_err:
                         min_err = avg_err
                         best_shift = shift
             
             start_y_est += best_shift

        GLOBAL_ROWS = []
        for r in range(18):
            GLOBAL_ROWS.append(int(start_y_est + r * avg_h))
            
        print(f"[{filename}] Global Grid: StartY={start_y_est}, Stride={avg_h:.1f}")

        # --- LOAD ANSWER KEY (Moved per Fix) ---
        answer_key = {}
        key_path = "answer_key.json"
        
        if os.path.exists(key_path):
            try:
                with open(key_path, 'r') as f:
                    answer_key = json.load(f)
                # Ensure keys are strings
                answer_key = {str(k): int(v) for k, v in answer_key.items()}
            except Exception as e:
                print(f"Error loading answer key: {e}")
        else:
             print("No answer_key.json found. Creating default key (All 'A'). Please edit this file!")
             dummy_key = {str(q): 1 for q in range(1, 91)} 
             with open(key_path, 'w') as f:
                 json.dump(dummy_key, f, indent=4)
             answer_key = dummy_key
             
        question_counter = 1
        
        # FORCE 5 BLOCKS
        for block_number in range(5):
            # Expected Center X for this block
            expected_x = start_x_anchor + (block_number * avg_stride)
            
            # Use specific columns if found, otherwise predict
            matched_block = None
            min_dist = 1000
            for blk, center in zip(valid_blocks, block_centers):
                dist = abs(center - expected_x)
                if dist < 80 and dist < min_dist:
                    min_dist = dist
                    matched_block = blk
            
            target_col_xs = []
            if matched_block:
                matched_block.sort(key=lambda b: b[0])
                opt_cols = []
                curr_opt = [matched_block[0]]
                for i in range(1, len(matched_block)):
                     if matched_block[i][0] - matched_block[i-1][0] > 20: 
                          opt_cols.append(curr_opt)
                          curr_opt = [matched_block[i]]
                     else:
                          curr_opt.append(matched_block[i])
                opt_cols.append(curr_opt)
                if len(opt_cols) > 4: opt_cols = opt_cols[-4:]
                target_col_xs = [ int(sum([b[0] for b in c])/len(c)) for c in opt_cols]
            
            if not target_col_xs or len(target_col_xs) < 4:
                offsets = [-54, -18, 18, 54]
                target_col_xs = [int(expected_x + o) for o in offsets]
                cv2.circle(vis, (int(expected_x), roi_y1+20), 10, (0,0,255), -1)

            # --- USE GLOBAL ROWS ---
            ideal_rows = GLOBAL_ROWS
            
            # Read Digits
            for r_idx, y_center in enumerate(ideal_rows):
                # Ensure y_center is within image
                if y_center >= roi_y2 or y_center <= roi_y1: continue

                q_num = question_counter
                
                answers_in_row = []
                
                # --- DIFFERENTIAL SCORING v4 (Balanced) ---
                counts = []
                # Helper to store box coords for visualization later
                box_coords = []
                
                for opt_idx, x_center in enumerate(target_col_xs):
                    # 1. Center Refinement
                    search_size = 12
                    sx1 = max(0, x_center - search_size)
                    sy1 = max(0, y_center - search_size)
                    sx2 = min(w, x_center + search_size)
                    sy2 = min(h, y_center + search_size)
                    
                    search_roi = thresh[sy1:sy2, sx1:sx2]
                    M = cv2.moments(search_roi)
                    if M["m00"] > 0:
                        x_center = sx1 + int(M["m10"] / M["m00"])
                        y_center = sy1 + int(M["m01"] / M["m00"])
                    
                    # Measure Box
                    box_size = 22
                    x1 = int(x_center - box_size//2)
                    y1 = int(y_center - box_size//2)
                    x2 = int(x_center + box_size//2)
                    y2 = int(y_center + box_size//2)
                    
                    box_coords.append((x1, y1, x2, y2))
                    
                    if x1 < 0 or y1 < 0 or x2 >= w or y2 >= h: 
                         counts.append((opt_idx+1, 0))
                         continue

                    # Hybrid Measure (Clean + Raw fallback?) 
                    # Actually Clean Thresh is best for standardizing, but Raw is better for faint.
                    # Let's stick to v3 but tune thresholds.
                    
                    mask = np.zeros(thresh.shape, dtype="uint8")
                    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
                    mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                    total = cv2.countNonZero(mask)
                    counts.append((opt_idx+1, total))

                # Analyze Counts
                counts.sort(key=lambda x: x[1], reverse=True)
                best = counts[0]
                second = counts[1]
                
                final_ans = 0
                
                # Logic v4: Higher Thresholds to stop overcorrection
                # 1. Absolute Mark: > 220 (Solid Fill) -> Accept
                # 2. Relative Mark: > 70 (Visible) AND > 25 diff (Distinct)
                # 3. Ratio: > 60 (Visible) AND > 2.0x Second (Dominant)
                
                if best[1] > 220:
                    final_ans = best[0]
                elif best[1] > 70 and (best[1] - second[1] > 25):
                     final_ans = best[0]
                elif best[1] > 60 and (second[1] == 0 or best[1] / second[1] > 2.0):
                     final_ans = best[0]
                
                # Retrieve Correct Answer from Key (if available)
                correct_ans = answer_key.get(str(q_num), -1)
                
                # --- VISUALIZATION ---
                # Draw Correct Answer (Blue Box)
                if correct_ans != -1 and 1 <= correct_ans <= 4:
                    cx1, cy1, cx2, cy2 = box_coords[correct_ans-1]
                    cv2.rectangle(vis, (cx1-2, cy1-2), (cx2+2, cy2+2), (255, 0, 0), 2) # Blue
                
                # Draw Detected Answer (Green/Red Box)
                if final_ans != 0:
                    dx1, dy1, dx2, dy2 = box_coords[final_ans-1]
                    color = (0, 255, 0) # Green (Correct)
                    if final_ans != correct_ans and correct_ans != -1:
                        color = (0, 0, 255) # Red (Wrong)
                    
                    cv2.rectangle(vis, (dx1, dy1), (dx2, dy2), color, 2)
                
                extracted_data["questions"].append({
                    "question": q_num,
                    "given_answer": final_ans
                })
                question_counter += 1
                
        # 2. Process Header (Area above question ROI)
                     
        # 2. Process Header (Area above question ROI)
        header_roi = image[0:roi_y1, :]
        gray_header = cv2.cvtColor(header_roi, cv2.COLOR_BGR2GRAY)
        
        # We can try to extract specific fields based on coordinates if we know them
        # For now, let's just get all text and do simple regex/splitting
        header_info = self.extract_header_text(gray_header)
        
        extracted_data["candidate_name"] = header_info.get("candidate_name", "Unknown")
        extracted_data["header_raw"] = header_info.get("raw_ocr", "")
        
        # --- GRADING LOGIC (Score Calculation) ---
        print(f"Loaded Answer Key for {len(answer_key)} questions.")
        
        score = 0
        correct_list = []
        wrong_list = []
        
        for q_item in extracted_data["questions"]:
            q_num = str(q_item["question"])
            given = q_item["given_answer"] # Integer 1-4 or 0
            
            if q_num in answer_key:
                correct_ans = answer_key[q_num]
                q_item["correct_answer"] = correct_ans
                
                if given == correct_ans:
                    q_item["status"] = "Correct"
                    score += 1
                    correct_list.append(q_num)
                elif given == 0:
                     q_item["status"] = "Unanswered"
                else:
                    q_item["status"] = "Wrong"
                    wrong_list.append(q_num)
            else:
                 q_item["status"] = "Unknown Key"
                 q_item["correct_answer"] = "?"

        extracted_data["score"] = score
        extracted_data["total_correct"] = len(correct_list)
        extracted_data["total_wrong"] = len(wrong_list)
        extracted_data["unanswered"] = 90 - (len(correct_list) + len(wrong_list))
        
        print(f"[{filename}] Processed. Score: {score}/90 | Correct: {len(correct_list)}")

        # Visualization: Draw Score on Image
        cv2.rectangle(vis, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 0, 0), 3) 
        
        # Color code the bubbles based on correctness? (Advanced)
        # For now, just simple text
        cv2.putText(vis, f"Score: {score}/90", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 200, 0), 5)
        
        out_path = f"debug_{filename}"
        cv2.imwrite(out_path, vis)
        
        return extracted_data

if __name__ == "__main__":
    omr = OMRSystem()
    img_dir = "images"
    results = []
    
    if os.path.exists(img_dir):
        files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.png'))]
        for f in files:
            path = os.path.join(img_dir, f)
            print(f"Processing {f}...")
            res = omr.process_image(path, f)
            if res:
                results.append(res)
    
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("Processing complete. Check results.json and debug images.")
