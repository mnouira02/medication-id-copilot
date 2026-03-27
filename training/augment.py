"""Few-shot augmentation for 3-class pill gate.

Input:
  data_raw/background/
  data_raw/ip/
  data_raw/not_ip/

Output:
  data/background/
  data/ip/
  data/not_ip/
"""

import cv2
import numpy as np
from pathlib import Path
import random

RAW_DIR = Path("data_raw")
OUT_DIR = Path("data")
IMG_SIZE = 224
AUGS_PER_IMAGE = 50

random.seed(42)
np.random.seed(42)

def load_and_resize(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not load {path}")
    return cv2.resize(img, (IMG_SIZE, IMG_SIZE))

def random_rotation(img, max_deg=30):
    angle = random.uniform(-max_deg, max_deg)
    M = cv2.getRotationMatrix2D((IMG_SIZE // 2, IMG_SIZE // 2), angle, 1.0)
    return cv2.warpAffine(img, M, (IMG_SIZE, IMG_SIZE), borderMode=cv2.BORDER_REFLECT)

def random_brightness(img, low=0.4, high=1.8):
    factor = random.uniform(low, high)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def random_contrast(img, low=0.6, high=1.6):
    mean = img.mean()
    return np.clip(mean + (img.astype(np.float32) - mean) * random.uniform(low, high), 0, 255).astype(np.uint8)

def random_blur(img):
    k = random.choice([0, 1, 3, 5, 7])
    if k == 0:
        return img
    return cv2.GaussianBlur(img, (k, k), 0)

def random_noise(img, intensity=15):
    noise = np.random.randint(-intensity, intensity, img.shape, dtype=np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

def random_flip(img):
    return cv2.flip(img, random.choice([-1, 0, 1]))

def random_zoom(img, min_crop=0.70):
    scale = random.uniform(min_crop, 1.0)
    size = int(IMG_SIZE * scale)
    x = random.randint(0, IMG_SIZE - size)
    y = random.randint(0, IMG_SIZE - size)
    crop = img[y:y+size, x:x+size]
    return cv2.resize(crop, (IMG_SIZE, IMG_SIZE))

def random_hue_shift(img, max_shift=15):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int32)
    hsv[:, :, 0] = (hsv[:, :, 0] + random.randint(-max_shift, max_shift)) % 180
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def random_perspective(img):
    margin = int(IMG_SIZE * 0.08)
    src = np.float32([[0,0],[IMG_SIZE,0],[IMG_SIZE,IMG_SIZE],[0,IMG_SIZE]])
    dst = np.float32([
        [random.randint(0, margin), random.randint(0, margin)],
        [IMG_SIZE-random.randint(0, margin), random.randint(0, margin)],
        [IMG_SIZE-random.randint(0, margin), IMG_SIZE-random.randint(0, margin)],
        [random.randint(0, margin), IMG_SIZE-random.randint(0, margin)]
    ])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (IMG_SIZE, IMG_SIZE), borderMode=cv2.BORDER_REFLECT)

def add_vignette(img):
    rows, cols = img.shape[:2]
    kx = cv2.getGaussianKernel(cols, cols * 0.7)
    ky = cv2.getGaussianKernel(rows, rows * 0.7)
    kernel = ky * kx.T
    mask = kernel / kernel.max()
    return (img * mask[:, :, np.newaxis]).astype(np.uint8)

AUGS = [
    random_rotation,
    random_brightness,
    random_contrast,
    random_blur,
    random_noise,
    random_flip,
    random_zoom,
    random_hue_shift,
    random_perspective,
    add_vignette,
]

def augment_image(img, n):
    results = []
    for _ in range(n):
        aug = img.copy()
        for fn in random.sample(AUGS, k=random.randint(3, 5)):
            aug = fn(aug)
        results.append(aug)
    return results

def process_class(cls):
    raw_path = RAW_DIR / cls
    out_path = OUT_DIR / cls
    out_path.mkdir(parents=True, exist_ok=True)

    files = list(raw_path.glob("*.jpg")) + list(raw_path.glob("*.jpeg")) + list(raw_path.glob("*.png"))
    if not files:
        raise FileNotFoundError(f"No files found in {raw_path}")

    total = 0
    print(f"\n[{cls}] Found {len(files)} source images")

    for src in files:
        img = load_and_resize(src)
        cv2.imwrite(str(out_path / f"orig_{src.name}"), img)
        total += 1

        for i, aug in enumerate(augment_image(img, AUGS_PER_IMAGE)):
            cv2.imwrite(str(out_path / f"aug_{src.stem}_{i:03d}.jpg"), aug)
            total += 1

    print(f"  ✅ Wrote {total} images to {out_path}")
    return total

if __name__ == "__main__":
    print("3-class few-shot augmentation")
    for cls in ["background", "ip", "not_ip"]:
        if (RAW_DIR / cls).exists():
            process_class(cls)
        else:
            print(f"⚠️ Missing {RAW_DIR / cls}")
    print("\n✅ Done. Now run: python train.py")