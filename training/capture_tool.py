"""Guided raw image capture for 3-class ROI training.

Usage:
  python capture_tool.py --class ip
  python capture_tool.py --class not_ip
  python capture_tool.py --class background
"""

import cv2
import os
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("--class", dest="cls", required=True, choices=["background", "ip", "not_ip"])
parser.add_argument("--output", default="data_raw")
parser.add_argument("--target", type=int, default=10)
args = parser.parse_args()

OUT_DIR = os.path.join(args.output, args.cls)
os.makedirs(OUT_DIR, exist_ok=True)

cap = cv2.VideoCapture(0)
count = len([f for f in os.listdir(OUT_DIR) if f.endswith((".jpg", ".jpeg", ".png"))])

TIPS = {
    "ip": [
        "Top-down, well-lit",
        "Slight left tilt",
        "Slight right tilt",
        "Close-up, fill the circle",
        "Further away",
        "Dim lighting",
        "Bright / backlit",
        "Dark background",
        "Light background",
        "Held in palm"
    ],
    "not_ip": [
        "Wrong pill, top-down",
        "Wrong pill, left tilt",
        "Wrong pill, right tilt",
        "Wrong pill, close-up",
        "Wrong pill, further away",
        "Wrong pill, dim lighting",
        "Wrong pill, bright lighting",
        "Wrong pill, dark background",
        "Wrong pill, light background",
        "Wrong pill, in palm"
    ],
    "background": [
        "Empty table",
        "Empty hand",
        "Nothing in ROI",
        "Finger covering ROI",
        "Blurry empty frame",
        "Dark room, empty ROI",
        "Bright room, empty ROI",
        "Pen or object, not a pill",
        "Phone / keys in ROI",
        "Random background"
    ]
}

print(f"Capturing [{args.cls}]")
print(f"Target: {args.target} images | Saved so far: {count}")
print("SPACE = save | Q = quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    roi_size = int(min(h, w) * 0.55)
    x1 = (w - roi_size) // 2
    y1 = (h - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size

    display = frame.copy()
    color = (160, 160, 160) if count < args.target else (0, 220, 120)
    cv2.circle(display, ((x1 + x2) // 2, (y1 + y2) // 2), roi_size // 2, color, 2)

    tip = TIPS[args.cls][min(count, len(TIPS[args.cls]) - 1)]
    cv2.putText(display, f"{count}/{args.target}: {tip}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    cv2.putText(display, "SPACE=save  Q=quit", (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)

    cv2.imshow("ROI Capture Tool", display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    elif key == ord(" "):
        crop = frame[y1:y2, x1:x2]
        crop = cv2.resize(crop, (224, 224))
        fname = os.path.join(OUT_DIR, f"{args.cls}_{int(time.time()*1000)}.jpg")
        cv2.imwrite(fname, crop)
        count += 1
        print(f"[{count}/{args.target}] Saved {fname}")

cap.release()
cv2.destroyAllWindows()
print(f"Done. {count} images 