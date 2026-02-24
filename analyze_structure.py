
import cv2
import numpy as np
import imutils
from collections import Counter
import os

def analyze_omr(image_path):
    print(f"Analyzing {image_path}...")
    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        return

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image at {image_path}")
        return

    print(f"Image Dimensions: {image.shape}")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Blur and Adaptive Threshold - trying to catch pencil marks
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 3)

    # Find contours
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    
    bubbles = []
    
    # Heuristics for Bubbles
    # Adjusting size filters - pencil marks might be slightly broken or lighter, but adaptive thresh should handle it.
    # Standard bubble size in high res scan might be larger.
    for c in cnts:
        (x, y, w, h) = cv2.boundingRect(c)
        ar = w / float(h)
        area = w * h
        
        # Keep relatively small things that are square-ish
        if w >= 15 and h >= 15 and w <= 60 and h <= 60 and ar >= 0.6 and ar <= 1.4:
            bubbles.append((x, y, w, h))

    print(f"Potential bubbles found: {len(bubbles)}")
    
    if len(bubbles) == 0:
        return

    # Analyze X-coordinates to find columns
    x_coords = [b[0] for b in bubbles]
    
    # Simple clustering of X coordinates
    # We round to nearest 50 to group them
    rounded_x = [int(x / 50) * 50 for x in x_coords]
    common_x = Counter(rounded_x).most_common()
    
    print("X-coordinate clusters (Approx Column positions):")
    # Sort by X position
    sorted_clusters = sorted(common_x, key=lambda x: x[0])
    for x_pos, count in sorted_clusters:
        if count > 10: # Filter out noise
            print(f"  X ~ {x_pos}: {count} bubbles")

    # Analyze Y-coordinates
    y_coords = [b[1] for b in bubbles]
    min_y, max_y = min(y_coords), max(y_coords)
    print(f"Y-coordinate range: {min_y} - {max_y}")
    
    # Top cluster of bubbles?
    # Maybe deduce row spacing
    row_heights = []
    bubbles_sorted_y = sorted(bubbles, key=lambda b: b[1])
    for i in range(1, len(bubbles_sorted_y)):
        diff = bubbles_sorted_y[i][1] - bubbles_sorted_y[i-1][1]
        if diff > 5 and diff < 100:
            row_heights.append(diff)
            
    if row_heights:
         avg_row_h = sum(row_heights)/len(row_heights)
         print(f"Average Row Spacing: {avg_row_h:.2f}")

if __name__ == "__main__":
    analyze_omr("img20260123_15145071.jpg")
