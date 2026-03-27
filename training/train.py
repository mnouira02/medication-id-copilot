"""3-class MobileNetV2 classifier for edge aDOT.

Classes:
  background = empty ROI / hand / table / no pill
  ip         = investigational product
  not_ip     = some pill, but not the investigational product

Exports TensorFlow.js model to ../frontend/public/model/
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model, regularizers
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import classification_report, confusion_matrix
import tensorflowjs as tfjs

DATA_DIR = "data"
OUTPUT_DIR = "../frontend/public/model"
IMG_SIZE = (224, 224)
BATCH_SIZE = 8
EPOCHS = 40

os.makedirs(OUTPUT_DIR, exist_ok=True)

train_gen = ImageDataGenerator(
    rescale=1.0 / 255,
    horizontal_flip=True,
    vertical_flip=True,
    rotation_range=10,
    zoom_range=0.1,
    validation_split=0.2
)

val_gen = ImageDataGenerator(
    rescale=1.0 / 255,
    validation_split=0.2
)

train_ds = train_gen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="training",
    shuffle=True,
    seed=42
)

val_ds = val_gen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation",
    shuffle=False,
    seed=42
)

class_indices = train_ds.class_indices
idx_to_class = {v: k for k, v in class_indices.items()}
num_classes = len(class_indices)

print("Classes:", class_indices)
print(f"Train samples: {train_ds.samples} | Val samples: {val_ds.samples}")

base = MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet"
)

base.trainable = False

x = base.output
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dense(128, activation="relu", kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.5)(x)
x = layers.Dense(32, activation="relu", kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.3)(x)
output = layers.Dense(num_classes, activation="softmax")(x)

model = Model(inputs=base.input, outputs=output)

print("\nPhase 1: training head...")
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-3),
    loss="categorical_crossentropy",
    metrics=["accuracy", tf.keras.metrics.AUC(name="auc", multi_label=True)]
)

callbacks1 = [
    tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True, monitor="val_loss"),
    tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=4, monitor="val_loss", verbose=1),
]

model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks1,
    verbose=1
)

print("\nPhase 2: fine-tuning top 30 layers...")
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False

model.compile(
    optimizer=tf.keras.optimizers.Adam(5e-5),
    loss="categorical_crossentropy",
    metrics=["accuracy", tf.keras.metrics.AUC(name="auc", multi_label=True)]
)

callbacks2 = [
    tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True, monitor="val_loss"),
    tf.keras.callbacks.ReduceLROnPlateau(factor=0.3, patience=4, monitor="val_loss", verbose=1),
]

model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks2,
    verbose=1
)

print("\n=== VALIDATION REPORT ===")
val_ds.reset()
pred_probs = model.predict(val_ds, verbose=0)
pred_idx = np.argmax(pred_probs, axis=1)
true_idx = val_ds.classes[:len(pred_idx)]

target_names = [idx_to_class[i] for i in range(num_classes)]
print(classification_report(true_idx, pred_idx, target_names=target_names))

cm = confusion_matrix(true_idx, pred_idx)
print("Confusion matrix:")
print(cm)

print(f"\nExporting TFJS model to {OUTPUT_DIR}...")
tfjs.converters.save_keras_model(model, OUTPUT_DIR)

meta = {
    "class_indices": class_indices,
    "idx_to_class": idx_to_class,
    "thresholds": {
        "background_neutral": 0.70,
        "ip_unlock": 0.90,
        "not_ip_alert": 0.85
    }
}
with open(os.path.join(OUTPUT_DIR, "class_map.json"), "w") as f:
    json.dump(meta, f, indent=2)

print("\n✅ Export complete:")
for fname in os.listdir(OUTPUT_DIR):
    path = os.path.join(OUTPUT_DIR, fname)
    print(f"  {fname}")