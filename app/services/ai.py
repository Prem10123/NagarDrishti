from collections import defaultdict
from io import BytesIO
from typing import Optional

from PIL import Image, ImageOps

from ..views import CATEGORY_NAMES

_model = None

# ImageNet labels civic issues poorly. Score many labels against our 18
# categories instead of returning "unknown" unless a tiny keyword list hits.
_SIGNALS: dict[int, tuple[tuple[str, float], ...]] = {
    1: (  # Dead animal(s)
        ("animal", 0.9), ("carcass", 1.0), ("dog", 0.85), ("cat", 0.85),
        ("bird", 0.7), ("hen", 0.75), ("cock", 0.7), ("rooster", 0.75),
        ("chick", 0.7), ("duck", 0.7), ("goose", 0.7), ("swan", 0.55),
        ("fox", 0.8), ("wolf", 0.75), ("pig", 0.8), ("hog", 0.8), ("boar", 0.75),
        ("ox", 0.8), ("cattle", 0.85), ("cow", 0.85), ("buffalo", 0.8),
        ("sheep", 0.8), ("ram", 0.7), ("goat", 0.8), ("horse", 0.7),
        ("donkey", 0.8), ("mule", 0.75), ("deer", 0.75), ("rabbit", 0.7),
        ("hare", 0.7), ("rat", 0.8), ("mouse", 0.65), ("squirrel", 0.6),
        ("mongoose", 0.75), ("snake", 0.7), ("cobra", 0.7), ("turtle", 0.55),
        ("frog", 0.55), ("toad", 0.6), ("lizard", 0.55), ("terrier", 0.85),
        ("retriever", 0.85), ("shepherd", 0.85), ("beagle", 0.85),
        ("spaniel", 0.85), ("hound", 0.8), ("poodle", 0.8), ("bulldog", 0.85),
        ("mastiff", 0.85), ("chihuahua", 0.85), ("corgi", 0.85), ("collie", 0.85),
        ("husky", 0.85), ("malamute", 0.85), ("boxer", 0.7), ("pug", 0.8),
        ("kitten", 0.85), ("tabby", 0.85), ("persian", 0.75), ("siamese", 0.75),
    ),
    2: (  # Dustbins not cleaned
        ("ashcan", 1.2), ("trash_can", 1.2), ("dustbin", 1.2), ("wastebin", 1.2),
        ("barrel", 0.55), ("rain_barrel", 0.7), ("bucket", 0.65),
        ("tub", 0.35), ("hamper", 0.55), ("crate", 0.4), ("mailbox", 0.35),
        ("tank", 0.25), ("safe", 0.15),
    ),
    3: (  # Garbage dump
        ("plastic_bag", 1.2), ("ashcan", 0.7), ("carton", 0.85),
        ("packet", 0.7), ("wrapper", 0.8), ("paper_towel", 0.55),
        ("toilet_tissue", 0.5), ("handkerchief", 0.35), ("envelope", 0.3),
        ("shopping_cart", 0.85), ("crate", 0.55), ("bottle", 0.45),
        ("pop_bottle", 0.7), ("water_bottle", 0.45), ("wine_bottle", 0.4),
        ("beer_bottle", 0.5), ("pill_bottle", 0.35), ("beer_can", 0.7),
        ("tin", 0.35), ("plate", 0.25), ("bowl", 0.2), ("cup", 0.15),
        ("coffee_mug", 0.2), ("tray", 0.3), ("backpack", 0.25),
        ("shoe", 0.25), ("sandal", 0.25), ("clog", 0.25), ("sock", 0.3),
        ("diaper", 0.9), ("band_aid", 0.35), ("banana", 0.25),
        ("orange", 0.2), ("pizza", 0.25), ("menu", 0.2),
    ),
    4: (  # Garbage vehicle not arrived
        ("garbage_truck", 1.4), ("trailer_truck", 0.9), ("tow_truck", 0.7),
        ("fire_engine", 0.45), ("moving_van", 0.55), ("pickup", 0.55),
        ("minivan", 0.4), ("jeep", 0.35), ("recreational_vehicle", 0.35),
        ("tractor", 0.45), ("harvester", 0.4), ("forklift", 0.4),
        ("snowplow", 0.4), ("streetcar", 0.25), ("trolleybus", 0.3),
        ("truck", 0.5), ("van", 0.3),
    ),
    5: (  # Sweeping not done
        ("broom", 1.3), ("mop", 1.1), ("vacuum", 0.7), ("washboard", 0.4),
        ("doormat", 0.55), ("sweeper", 1.0), ("dustpan", 0.9),
    ),
    6: (  # No electricity in public toilet
        ("toilet_seat", 0.55), ("washbasin", 0.4), ("switch", 0.7),
        ("table_lamp", 0.55), ("spotlight", 0.45), ("lantern", 0.5),
        ("flashlight", 0.55), ("candle", 0.4), ("lampshade", 0.4),
        ("television", 0.25), ("monitor", 0.15),
    ),
    7: (  # No water supply in public toilet
        ("washbasin", 0.9), ("bathtub", 0.55), ("water_bottle", 0.45),
        ("water_jug", 0.7), ("pitcher", 0.45), ("fountain", 0.55),
        ("water_tower", 0.4), ("geyser", 0.35), ("cup", 0.15),
        ("toilet_seat", 0.35),
    ),
    8: (  # Public toilet blockage
        ("toilet_seat", 1.15), ("washbasin", 0.55), ("plunger", 1.3),
        ("toilet_tissue", 0.7), ("paper_towel", 0.4), ("septic", 0.8),
    ),
    9: (  # Public toilet cleaning
        ("toilet_seat", 0.9), ("washbasin", 0.8), ("soap_dispenser", 1.2),
        ("bathtub", 0.45), ("mop", 0.7), ("broom", 0.45), ("paper_towel", 0.45),
        ("dishwasher", 0.25), ("washer", 0.35), ("vacuum", 0.25),
    ),
    10: (  # Open manholes / potholes
        ("manhole", 1.4), ("sewer", 1.0), ("drain", 0.9), ("grate", 0.85),
        ("strainer", 0.45), ("disk_brake", 0.55), ("doormat", 0.35),
        ("tile_roof", 0.25), ("stone_wall", 0.35), ("cobblestone", 0.55),
        ("pothole", 1.4), ("asphalt", 0.7), ("pavement", 0.55),
        ("street_sign", 0.45), ("traffic_light", 0.4), ("parking_meter", 0.4),
        ("fire_hydrant", 0.45), ("manhole_cover", 1.4), ("hole", 0.5),
        ("maze", 0.2), ("valley", 0.15), ("cliff", 0.15),
        ("motor_scooter", 0.2), ("moped", 0.2), ("mountain_bike", 0.2),
    ),
    11: (  # Overflow of sewerage
        ("sewer", 1.2), ("drain", 0.8), ("lakeside", 0.45), ("fountain", 0.35),
        ("breakwater", 0.3), ("dam", 0.35), ("dock", 0.25), ("puddle", 0.8),
        ("sludge", 1.0), ("pipe", 0.4), ("culvert", 0.8),
    ),
    12: (  # Stagnant water
        ("lakeside", 0.85), ("seashore", 0.55), ("lakeshore", 0.85),
        ("swimming_pool", 0.7), ("fountain", 0.55), ("rapids", 0.35),
        ("waterfall", 0.3), ("dock", 0.35), ("breakwater", 0.4),
        ("boathouse", 0.3), ("canoe", 0.3), ("paddle", 0.25),
        ("water_snake", 0.35), ("puddle", 1.0), ("pond", 0.9),
        ("wetland", 0.8), ("marsh", 0.8),
    ),
    13: (  # Improper disposal of fecal waste
        ("toilet_tissue", 0.7), ("toilet_seat", 0.45), ("diaper", 0.9),
        ("ashcan", 0.25), ("plastic_bag", 0.3),
    ),
    14: (  # Debris removal
        ("wreck", 1.1), ("stone_wall", 0.45), ("cliff", 0.3), ("megalith", 0.4),
        ("barn", 0.25), ("thatch", 0.35), ("crane", 0.4), ("tractor", 0.3),
        ("pickup", 0.25), ("chain_saw", 0.4), ("lumbermill", 0.45),
        ("brick", 0.35), ("ruins", 0.8), ("rubble", 1.2), ("debris", 1.2),
        ("dumpster", 0.7),
    ),
    15: (  # Burning of garbage
        ("volcano", 0.7), ("fire", 1.3), ("flame", 1.3), ("stove", 0.45),
        ("barbecue", 0.7), ("grill", 0.55), ("lighter", 0.6),
        ("matchstick", 0.7), ("candle", 0.35), ("torch", 0.7),
        ("bonfire", 1.2), ("smoke", 0.9),
    ),
    16: (  # Open defecation
        ("toilet_seat", 0.25), ("lakeside", 0.15), ("valley", 0.12),
        ("outhouse", 0.8),
    ),
    17: (  # Overflow of septic tanks
        ("barrel", 0.55), ("rain_barrel", 0.65), ("tank", 0.5),
        ("tub", 0.4), ("water_tower", 0.4), ("septic", 1.2),
        ("cistern", 0.9), ("sewer", 0.55),
    ),
    18: (  # Yellow spot (urination)
        ("wall", 0.15), ("stone_wall", 0.25), ("doormat", 0.2),
        ("street_sign", 0.15),
    ),
}

_SUGGEST_MIN = 0.045
_ENFORCE_MIN = 0.28


def get_model():
    global _model
    if _model is None:
        import tensorflow as tf

        print("Loading ResNet50 Model...")
        _model = tf.keras.applications.ResNet50(weights="imagenet")
        print("AI Model Loaded.")
    return _model


def _letterbox(img: Image.Image, size: int = 224) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    scale = size / max(w, h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = img.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("RGB", (size, size), (123, 117, 104))
    canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2))
    return canvas


def _bottom_crop(img: Image.Image) -> Image.Image:
    w, h = img.size
    top = int(h * 0.32)
    if h - top < 32:
        return img
    return img.crop((0, top, w, h))


def _label_hits(label: str, keyword: str) -> bool:
    if keyword == label:
        return True
    if "_" in keyword:
        return keyword in label
    return keyword in label.split("_")


def _color_priors(img: Image.Image) -> dict[int, float]:
    sample = img.convert("RGB").resize((64, 64), Image.BILINEAR)
    pixels = list(sample.getdata())
    n = float(len(pixels))
    fire = water = yellow = gray = colorful = 0.0
    for r, g, b in pixels:
        mx = max(r, g, b)
        mn = min(r, g, b)
        mean = (r + g + b) / 3.0
        if r > 145 and r > g + 18 and r > b + 28 and g > b:
            fire += 1
        if mean < 115 and (b + 18) >= r and abs(g - b) < 42:
            water += 1
        if r > 145 and g > 125 and b < 95 and r > b + 45:
            yellow += 1
        if abs(r - g) < 16 and abs(g - b) < 16 and 45 < mean < 145:
            gray += 1
        if mx - mn > 55:
            colorful += 1
    priors: dict[int, float] = defaultdict(float)
    fire_f, water_f, yellow_f = fire / n, water / n, yellow / n
    gray_f, color_f = gray / n, colorful / n
    if fire_f > 0.04:
        priors[15] += min(0.16, fire_f * 0.55)
    if water_f > 0.12:
        priors[12] += min(0.14, water_f * 0.4)
        priors[11] += min(0.08, water_f * 0.22)
        priors[17] += min(0.05, water_f * 0.12)
    if yellow_f > 0.08:
        priors[18] += min(0.12, yellow_f * 0.45)
        priors[15] += min(0.04, yellow_f * 0.1)
    if gray_f > 0.28:
        priors[10] += min(0.1, (gray_f - 0.2) * 0.35)
        priors[14] += min(0.05, (gray_f - 0.2) * 0.15)
    if color_f > 0.22:
        priors[3] += min(0.07, (color_f - 0.18) * 0.25)
    return priors


def _accumulate(decoded, scores: dict[int, float]) -> None:
    for _code, label, prob in decoded:
        if prob < 0.008:
            continue
        label = label.lower().replace("-", "_")
        for cat_id, keywords in _SIGNALS.items():
            for keyword, weight in keywords:
                if _label_hits(label, keyword):
                    scores[cat_id] += float(prob) * weight
                    break


def _pick(scores: dict[int, float]) -> tuple[Optional[int], float]:
    if not scores:
        return None, 0.0
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_id, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    if best < _SUGGEST_MIN:
        return None, best
    if best < 0.09 and best < second + 0.018:
        return None, best
    return best_id, best


def detect_category_from_bytes(image_bytes: bytes) -> tuple[Optional[int], Optional[str], float]:
    try:
        import numpy as np
        import tensorflow as tf

        model = get_model()
        with Image.open(BytesIO(image_bytes)) as raw:
            img = ImageOps.exif_transpose(raw).convert("RGB").copy()

        views = [img, _bottom_crop(img)]
        batch = np.stack(
            [tf.keras.preprocessing.image.img_to_array(_letterbox(view)) for view in views],
            axis=0,
        )
        batch = tf.keras.applications.resnet50.preprocess_input(batch)
        preds = model.predict(batch, verbose=0)
        blended = np.mean(preds, axis=0, keepdims=True)
        decoded = tf.keras.applications.resnet50.decode_predictions(blended, top=25)[0]

        scores: dict[int, float] = defaultdict(float)
        _accumulate(decoded, scores)
        color = _color_priors(img)
        for cat_id, bonus in color.items():
            if scores.get(cat_id, 0) > 0:
                scores[cat_id] += bonus
        # Fire color is distinctive enough to suggest on its own.
        if not scores.get(15) and color.get(15, 0) >= 0.12:
            scores[15] = color[15]

        cat_id, conf = _pick(scores)
        if cat_id is None:
            return None, None, float(conf)
        return cat_id, CATEGORY_NAMES[cat_id], float(conf)
    except Exception as exc:
        print(f"AI Error: {exc}")
        return None, None, 0.0


def detection_is_strict(category_id: Optional[int], confidence: float) -> bool:
    from ..views import STRICT_CATEGORIES

    return bool(category_id and category_id in STRICT_CATEGORIES and confidence >= _ENFORCE_MIN)
