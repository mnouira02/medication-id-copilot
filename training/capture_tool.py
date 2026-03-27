"""Webcam capture tool for collecting training images.

Usage:
  python capture_tool.py --class ip      # capture investigational product photos
  python capture_tool.py --class not_ip  # capture background/wrong pill photos

Controls:
  SPACE  = save current frame
  Q      = quit

Target: ~150 images per class from varied angles, lighting, distances.
"""

import cv2
import os
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("--class", dest="cls", required=True, choices=["ip", "not_ip"])
parser.add_argument("--output", default="data")
args = parser.parse_args()

OUT_DIR = os.path.join(args.output, args.cls)
os.makedirs(OUT_DIR, exist_ok=True)

cap = cv2.VideoCapture(0)
count = len(os.listdir(OUT_DIR))

print(f"Capturing [{args.cls}] images. SPACE=save, Q=quit. Saved so far: {count}")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    size = min(h, w)
    roi_size = int(size * 0.55)
    x1 = (w - roi_size) // 2
    y1 = (h - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size

    display = frame.copy()
    cv2.rectangle(display, (x1, y1), (x2, y2), (0, 200, 255), 2)
    cv2.putText(display, f"Class: {args.cls} | Saved: {count} | SPACE=save Q=quit",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
    cv2.imshow("Capture Tool", display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(' '):
        crop = frame[y1:y2, x1:x2]
        crop_resized = cv2.resize(crop, (224, 224))
        fname = os.path.join(OUT_DIR, f"{args.cls}_{int(time.time()*1000)}.jpg")
        cv2.imwrite(fname, crop_resized)
        count += 1
        print(f"  Saved {fname} ({count} total)")

cap.release()
cv2.destroyAllWindows()
print(f"Done. {count} images saved to {OUT_DIR}/")
