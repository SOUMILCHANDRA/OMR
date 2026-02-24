
import cv2
import numpy as np
try:
    import imutils
    print("imutils imported successfully")
except ImportError:
    print("imutils not found")
import sys

print(f"Python version: {sys.version}")
print(f"OpenCV version: {cv2.__version__}")

img = cv2.imread('img20260123_15145071.jpg')
if img is not None:
    print(f"Image loaded: {img.shape}")
else:
    print("Failed to load image")
