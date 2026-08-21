from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AIStyleMetadata:
    id: str
    display_name: str
    display_name_vi: str
    description: str
    category: str
    voice_mode: str = "single"
    speaker_roles: tuple[str, ...] = ("narrator",)
    role_labels: tuple[str, ...] = ("Narrator",)

    @property
    def voice_count_label(self):
        return {"single": "1 Voice", "dual": "2 Voices", "triple": "3 Voices", "multi": "Multi Voice"}[self.voice_mode]


_STYLE_ROWS = [
    ("factory_documentary", "Factory documentary", "Tài liệu nhà máy", "Clear process-focused factory narration", "Documentary"),
    ("fast_viral_explainer", "Fast viral explainer", "Giải thích nhanh, cuốn hút", "Fast hooks and compact explanations", "Social"),
    ("calm_documentary", "Calm documentary", "Tài liệu nhẹ nhàng", "Measured and natural documentary narration", "Documentary"),
    ("technical_explainer", "Technical explainer", "Giải thích kỹ thuật", "Mechanisms, details, and specifications", "Engineering"),
    ("how_it_works", "How it works", "Cách hoạt động", "Step-by-step operating principles", "Educational"),
    ("engineering_breakdown", "Engineering breakdown", "Phân tích kỹ thuật / Cơ khí", "Break down construction and design choices", "Engineering"),
    ("mega_machines", "Mega machines", "Máy móc khổng lồ", "Scale, power, and impressive machinery", "Engineering"),
    ("manufacturing_process", "Manufacturing process", "Quy trình sản xuất", "Follow production from material to product", "Factory"),
    ("satisfying_process", "Satisfying process", "Quy trình mãn nhãn", "Sparse narration for satisfying visuals", "Factory"),
    ("invention_showcase", "Invention showcase", "Giới thiệu phát minh", "Problem, invention, operation, and value", "Discovery"),
    ("innovation_story", "Innovation story", "Câu chuyện đổi mới", "From practical need to new solution", "Discovery"),
    ("before_after", "Before & After", "Trước và Sau", "Contrast the state before and the result after", "Story", "dual", ("before", "after"), ("Before", "After")),
    ("product_teardown", "Product teardown", "Mổ xẻ sản phẩm", "Inside components and how they work together", "Engineering"),
    ("science_discovery", "Science and discovery", "Khoa học & Khám phá", "Explain visible evidence with scientific reasoning", "Discovery"),
    ("history_documentary", "History documentary", "Tài liệu lịch sử", "Context, chronology, causes, and effects", "Documentary"),
    ("news_report", "News report", "Phong cách tin tức", "Concise neutral facts and events", "Information"),
    ("business_case_study", "Business case study", "Tình huống kinh doanh", "Problem, strategy, result, and lesson", "Information"),
    ("motivational", "Motivational", "Truyền cảm hứng", "Positive energy and achievement", "Story"),
    ("storytelling_documentary", "Storytelling documentary", "Tài liệu kể chuyện", "Narrative arc with conflict and resolution", "Story"),
    ("mystery_curiosity", "Mystery & Curiosity", "Bí ẩn & Khơi gợi tò mò", "Question hook followed by an explanatory reveal", "Story", "dual", ("questioner", "explainer"), ("Question / Hook", "Answer / Explanation")),
    ("top_list", "Top 10 countdown", "Danh sách nổi bật", "A paced countdown that builds curiosity", "Social"),
    ("comparison", "Comparison", "So sánh", "Contrast strengths, weaknesses, and value", "Information"),
    ("educational", "Educational lesson", "Kiến thức / Giáo dục", "Definitions followed by clear examples", "Educational"),
    ("beginner_friendly", "Beginner friendly", "Dành cho người mới", "Simple language with immediate definitions", "Educational"),
    ("expert_deep_dive", "Expert deep dive", "Phân tích chuyên sâu", "Detailed explanation for informed viewers", "Engineering"),
    ("cinematic_narration", "Cinematic narration", "Thuyết minh điện ảnh", "Visual language and dramatic pacing", "Story"),
    ("high_energy_shorts", "High-energy shorts", "Video ngắn giàu năng lượng", "Very short lines and frequent hooks", "Social"),
    ("luxury_documentary", "Luxury documentary", "Tài liệu cao cấp", "Refined pacing and craftsmanship", "Documentary"),
    ("agriculture_machinery", "Agriculture and machinery", "Nông nghiệp & Máy móc", "Field work, productivity, and mechanization", "Engineering"),
    ("construction_equipment", "Construction and heavy equipment", "Xây dựng & Thiết bị hạng nặng", "Worksites, loads, safety, and performance", "Engineering"),
    ("automotive_engineering", "Automotive engineering", "Kỹ thuật ô tô", "Powertrain, chassis, and vehicle technology", "Engineering"),
    ("aerospace_engineering", "Aerospace engineering", "Kỹ thuật hàng không", "Materials, aerodynamics, and flight systems", "Engineering"),
    ("technology_innovation", "Technology innovation", "Đổi mới công nghệ", "New technology, applications, and impact", "Discovery"),
    ("environmental_documentary", "Environmental documentary", "Tài liệu môi trường", "Resources, impact, solutions, and sustainability", "Documentary"),
    ("food_production", "Food production", "Sản xuất thực phẩm", "Ingredients, processing, and quality control", "Factory"),
    ("travel_documentary", "Travel documentary", "Tài liệu du lịch", "Places, culture, experience, and local stories", "Documentary"),
    ("human_interest", "Human interest story", "Câu chuyện con người", "People, emotion, and lived experience", "Story"),
    ("problem_solution", "Problem & Solution", "Vấn đề & Giải pháp", "Present the problem, then explain the solution", "Educational", "dual", ("problem", "solution"), ("Problem", "Solution")),
    ("myth_fact", "Myth vs fact", "Hiểu lầm & Sự thật", "Compare common beliefs with evidence", "Educational"),
    ("data_explainer", "Data driven explainer", "Giải thích bằng dữ liệu", "Use quantities and comparisons carefully", "Information"),
    ("interview", "Interview", "Phỏng vấn", "Host prompts and guest responses", "Conversation", "dual", ("host", "guest"), ("Host", "Guest")),
    ("question_answer", "Question & Answer", "Hỏi & Đáp", "Semantic questions followed by answers", "Conversation", "dual", ("questioner", "answerer"), ("Question", "Answer")),
    ("debate", "Debate", "Tranh luận", "Two viewpoints responding to each other", "Conversation", "dual", ("speaker_a", "speaker_b"), ("Speaker A", "Speaker B")),
]

AI_STYLES = tuple(AIStyleMetadata(*row) for row in _STYLE_ROWS)
STYLE_BY_ID = {style.id: style for style in AI_STYLES}
STYLE_BY_DISPLAY = {style.display_name: style for style in AI_STYLES}
VOICE_MODE_ORDER = ("single", "dual", "triple", "multi")
VOICE_MODE_LABELS = {"single": "1 GIỌNG / SINGLE VOICE", "dual": "2 GIỌNG / DUAL VOICE", "triple": "3 GIỌNG / TRIPLE VOICE", "multi": "NHIỀU GIỌNG / MULTI VOICE"}


def get_style(value: str) -> AIStyleMetadata:
    aliases = {"Before and after": "before_after", "Mystery and curiosity": "mystery_curiosity", "Problem solution explainer": "problem_solution"}
    key = aliases.get(str(value), str(value))
    return STYLE_BY_ID.get(key, STYLE_BY_DISPLAY.get(key, AI_STYLES[0]))


def grouped_styles():
    return {mode: tuple(style for style in AI_STYLES if style.voice_mode == mode) for mode in VOICE_MODE_ORDER}
