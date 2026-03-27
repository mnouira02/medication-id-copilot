"""MobileNetV2 binary classifier training script.

Classes:
  0 = ip       (Investigational Product)
  1 = not_ip   (Background / wrong pills / hand / empty)

Outputs a TensorFlow.js model to frontend/public/model/
so it can be loaded directly in the browser with zero backend inference.
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import classification_report
import tensorflowjs as tfjs

# --- Config ---
DATA_DIR    = "data"
OUTPUT_DIR  = "../frontend/public/model"
IMG_SIZE    = (224, 224)
BATCH_SIZE  = 16
EPOCHS      = 30
CONF_THRESH = 0.90   # threshold used in frontend too

os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- Data ---
train_gen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    width_shift_range=0.1,
    height_shift_range=0.1,
    brightness_range=[0.6, 1.4],   # simulate poor lighting
    zoom_range=0.2,
    horizontal_flip=True,
    validation_split=0.2
)

train_ds = train_gen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="binary",
    subset="training",
    seed=42
)

val_ds = train_gen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="binary",
    subset="validation",
    seed=42
)

print(f"Classes: {train_ds.class_indices}")
# Expected: {'ip': 0, 'not_ip': 1}


# --- Model: MobileNetV2 fine-tuned ---
base = MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights="imagenet")

# Freeze all layers except the last 20 (fine-tune top of base + new head)
for layer in base.layers[:-20]:
    layer.trainable = False

x = base.output
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
x = layers.Dense(64, activation="relu")(x)
x = layers.Dropout(0.2)(x)
output = layers.Dense(1, activation="sigmoid")(x)  # binary sigmoid

model = Model(inputs=base.input, outputs=output)

model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-4),
    loss="binary_crossentropy",
    metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
)

model.summary()


# --- Callbacks ---
callbacks = [
    tf.keras.callbacks.EarlyStopping(patience=7, restore_best_weights=True, monitor="val_auc"),
    tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3, monitor="val_loss"),
]


# --- Train ---
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)


# --- Evaluate ---
print("\n--- Validation Report ---")
val_ds.reset()
y_pred_proba = model.predict(val_ds)
y_pred = (y_pred_proba > CONF_THRESH).astype(int).flatten()
y_true = val_ds.classes[:len(y_pred)]
print(classification_report(y_true, y_pred, target_names=["ip", "not_ip"]))


# --- Export to TensorFlow.js ---
print(f"\nExporting TFJS model to {OUTPUT_DIR}...")
tfjs.converters.save_keras_model(model, OUTPUT_DIR)

# Save class map so frontend knows which index = IP
class_map = {v: k for k, v in train_ds.class_indices.items()}
with open(os.path.join(OUTPUT_DIR, "class_map.json"), "w") as f:
    json.dump(class_map, f, indent=2)

print("\n✅ Done. Model exported to:", OUTPUT_DIR)
print("   Drop frontend/public/model/ into your Next.js app and run npm run dev.")
