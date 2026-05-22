"""Flo-style tag catalog.

Categories and tag_keys are PYTHON CONSTANTS. To add/rename a tag, edit this
file + write a migration if the change is destructive (i.e., removes a tag_key
that has existing rows in daily_tags).

The DB stores (category, tag_key) tuples in daily_tags; this module is the
source of truth for what tag_keys are valid and how to render them.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    """A single selectable tag in the Flo-style sheet."""
    key: str        # stored in DB (stable identifier; English snake_case)
    label: str      # display label (Chinese)
    emoji: str      # leading icon
    category: str   # which group it belongs to (foreign reference to Category.key)


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    order: int = 0


# Categories — ordered as they appear in the "Today" sheet
CATEGORIES: tuple[Category, ...] = (
    Category(key="sex",         label="性行为和性欲", order=10),
    Category(key="mood",        label="心情",        order=20),
    Category(key="symptoms",    label="症状",        order=30),
    Category(key="discharge",   label="阴道分泌物",   order=40),
    Category(key="digestion",   label="消化和排便",   order=50),
    Category(key="ovulation",   label="排卵测试",    order=60),
    Category(key="other",       label="其他",        order=70),
)


# Tags — order within each category roughly follows the screenshots
TAGS: tuple[Tag, ...] = (
    # === Sex & libido ===
    Tag("no_sex",            "没有性行为",     "🚫", "sex"),
    Tag("protected_sex",     "有保护的性行为", "🛡", "sex"),
    Tag("unprotected_sex",   "无保护的性行为", "🔓", "sex"),
    Tag("oral_sex",          "口交",          "💋", "sex"),
    Tag("anal_sex",          "肛交",          "🍑", "sex"),
    Tag("masturbation",      "自慰",          "💗", "sex"),
    Tag("foreplay",          "爱抚",          "💞", "sex"),
    Tag("sex_toys",          "情趣用品",       "✨", "sex"),
    Tag("orgasm",            "性高潮",        "💫", "sex"),
    Tag("libido_high",       "性欲旺盛",       "❤️", "sex"),
    Tag("libido_average",    "性欲一般",       "🙂", "sex"),
    Tag("libido_low",        "性欲低下",       "🤍", "sex"),

    # === Mood ===
    Tag("mood_calm",         "平静",          "😌", "mood"),
    Tag("mood_happy",        "快乐",          "😊", "mood"),
    Tag("mood_energetic",    "有活力",        "🤩", "mood"),
    Tag("mood_playful",      "欢悦",          "😜", "mood"),
    Tag("mood_swings",       "情绪波动",       "😢", "mood"),
    Tag("mood_irritable",    "恼怒",          "😠", "mood"),
    Tag("mood_sad",          "伤心",          "😞", "mood"),
    Tag("mood_anxious",      "焦虑",          "😨", "mood"),
    Tag("mood_depressed",    "抑郁",          "😔", "mood"),
    Tag("mood_guilty",       "内疚",          "😟", "mood"),

    # === Symptoms ===
    Tag("sym_all_fine",      "一切正常",       "👍", "symptoms"),
    Tag("sym_cramps",        "绞痛",          "🩸", "symptoms"),
    Tag("sym_breast_tender", "乳房压痛",       "💗", "symptoms"),
    Tag("sym_headache",      "头痛",          "🤕", "symptoms"),
    Tag("sym_acne",          "粉刺",          "🫧", "symptoms"),
    Tag("sym_backache",      "背痛",          "🦴", "symptoms"),
    Tag("sym_fatigue",       "疲倦",          "🔋", "symptoms"),
    Tag("sym_cravings",      "渴望",          "🍰", "symptoms"),
    Tag("sym_insomnia",      "失眠",          "😴", "symptoms"),
    Tag("sym_abdominal_pain","腹痛",          "🩸", "symptoms"),
    Tag("sym_vag_itch",      "阴道瘙痒",       "💧", "symptoms"),
    Tag("sym_vag_dry",       "阴道干涩",       "🏜", "symptoms"),

    # === Vaginal discharge ===
    Tag("disch_none",        "无分泌物",       "🚫", "discharge"),
    Tag("disch_creamy",      "乳液状",        "🥛", "discharge"),
    Tag("disch_watery",      "水状",          "💧", "discharge"),
    Tag("disch_sticky",      "粘稠",          "🧴", "discharge"),
    Tag("disch_egg_white",   "蛋清状",        "🥚", "discharge"),
    Tag("disch_spotting",    "点滴出血",       "🩸", "discharge"),
    Tag("disch_abnormal",    "异常",          "⚠️", "discharge"),
    Tag("disch_lumpy",       "白色块状",       "🧀", "discharge"),
    Tag("disch_grey",        "灰色",          "⚪", "discharge"),

    # === Digestion ===
    Tag("dig_nausea",        "恶心",          "🤢", "digestion"),
    Tag("dig_bloating",      "腹胀",          "🎈", "digestion"),
    Tag("dig_constipation",  "便秘",          "🔒", "digestion"),
    Tag("dig_diarrhea",      "腹泻",          "💩", "digestion"),

    # === Ovulation test (LH strip) ===
    Tag("ovu_not_tested",    "没有进行测试",    "🚷", "ovulation"),
    Tag("ovu_positive",      "阳性",          "🟢", "ovulation"),
    Tag("ovu_negative",      "阴性",          "🔴", "ovulation"),
    Tag("ovu_faint",         "晕线",          "🟡", "ovulation"),

    # === Other lifestyle ===
    Tag("other_travel",      "旅行",          "✈️", "other"),
    Tag("other_stress",      "压力",          "⚡", "other"),
    Tag("other_meditation",  "冥想",          "🧘", "other"),
    Tag("other_journal",     "写日记",        "📔", "other"),
    Tag("other_kegel",       "凯格尔训练",     "💪", "other"),
    Tag("other_breathing",   "呼吸练习",       "🫁", "other"),
    Tag("other_illness",     "疾病或损伤",     "🩹", "other"),
    Tag("other_alcohol",     "酒精",          "🍷", "other"),
)


# Convenience lookups
TAG_BY_KEY: dict[str, Tag] = {t.key: t for t in TAGS}
TAGS_BY_CATEGORY: dict[str, tuple[Tag, ...]] = {
    cat.key: tuple(t for t in TAGS if t.category == cat.key)
    for cat in CATEGORIES
}


def is_valid_tag(key: str) -> bool:
    """True iff `key` exists in the catalog."""
    return key in TAG_BY_KEY


def is_valid_category(key: str) -> bool:
    return any(c.key == key for c in CATEGORIES)


def category_of(tag_key: str) -> str:
    """Return the category.key of the given tag.key (raises KeyError if unknown)."""
    return TAG_BY_KEY[tag_key].category
