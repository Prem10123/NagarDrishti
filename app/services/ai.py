from io import BytesIO
from typing import Optional

from PIL import Image

from ..views import CATEGORY_NAMES, STRICT_CATEGORIES

_model = None


def get_model():
    global _model
    if _model is None:
        import tensorflow as tf

        print("Loading ResNet50 Model...")
        _model = tf.keras.applications.ResNet50(weights="imagenet")
        print("AI Model Loaded.")
    return _model


def detect_category_from_bytes(image_bytes: bytes) -> tuple[Optional[int], Optional[str]]:
    try:
        import numpy as np
        import tensorflow as tf

        model = get_model()
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGB").resize((224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img)

        img_array = np.expand_dims(img_array, axis=0)
        img_array = tf.keras.applications.resnet50.preprocess_input(img_array)
        preds = model.predict(img_array, verbose=0)
        decoded = tf.keras.applications.resnet50.decode_predictions(preds, top=10)[0]

        for (_code, label, score) in decoded:
            label = label.lower()
            if score < 0.02:
                continue
            for cat_id, keywords in STRICT_CATEGORIES.items():
                if any(k in label for k in keywords) or any(label in k for k in keywords):
                    return cat_id, CATEGORY_NAMES[cat_id]
        return None, None
    except Exception as exc:
        print(f"AI Error: {exc}")
        return None, None
