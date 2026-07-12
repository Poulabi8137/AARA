"""20-question research benchmark suite across 7 categories.

Each question includes expected findings, subtopics, references, and quality
expectations to enable objective scoring of AARA's research output quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BenchmarkQuestion:
    id: str
    category: str
    query: str
    difficulty: str  # basic, intermediate, advanced
    objective: str
    expected_findings: list[str] = field(default_factory=list)
    expected_subtopics: list[str] = field(default_factory=list)
    expected_references: list[str] = field(default_factory=list)
    expected_quality_score: float = 70.0
    description: str = ""
    tags: list[str] = field(default_factory=list)


BENCHMARK_20_QUESTIONS: list[BenchmarkQuestion] = [
    # ── Category 1: Artificial Intelligence ──────────────────────────
    BenchmarkQuestion(
        id="AI-01",
        category="Artificial Intelligence",
        query="What are the key challenges in aligning large language models with human values?",
        difficulty="advanced",
        objective="Identify technical approaches, philosophical challenges, and evaluation methods for LLM alignment.",
        expected_findings=[
            "reward hacking",
            "scalable oversight",
            "specification gaming",
            "value learning",
            "RLHF limitations",
        ],
        expected_subtopics=[
            "RLHF",
            "constitutional AI",
            "debate and amplification",
            "interpretability",
            "evaluation benchmarks",
        ],
        expected_references=[
            "https://arxiv.org/abs/2211.09110",
            "https://arxiv.org/abs/2203.02155",
        ],
        expected_quality_score=75.0,
        tags=["ai", "alignment", "safety"],
    ),
    BenchmarkQuestion(
        id="AI-02",
        category="Artificial Intelligence",
        query="How do transformer architectures compare to state space models for long-context sequence modeling?",
        difficulty="intermediate",
        objective="Compare attention mechanisms, computational complexity, and empirical performance across model families.",
        expected_findings=[
            "quadratic attention bottleneck",
            "linear state space models",
            "Mamba architecture",
            "selective state spaces",
        ],
        expected_subtopics=[
            "transformers",
            "state space models",
            "long-context efficiency",
            "hybrid architectures",
        ],
        expected_references=[
            "https://arxiv.org/abs/2312.00752",
        ],
        expected_quality_score=70.0,
        tags=["ai", "transformers", "architectures"],
    ),
    BenchmarkQuestion(
        id="AI-03",
        category="Artificial Intelligence",
        query="What methods exist for detecting and mitigating bias in machine learning models?",
        difficulty="basic",
        objective="Survey bias detection techniques, fairness metrics, and debiasing strategies across the ML pipeline.",
        expected_findings=[
            "demographic parity",
            "equal opportunity",
            "adversarial debiasing",
            "fairness constraints",
        ],
        expected_subtopics=[
            "bias detection",
            "fairness metrics",
            "debiasing methods",
            "auditing frameworks",
        ],
        expected_references=[
            "https://arxiv.org/abs/1810.01943",
        ],
        expected_quality_score=70.0,
        tags=["ai", "bias", "fairness"],
    ),
    BenchmarkQuestion(
        id="AI-04",
        category="Artificial Intelligence",
        query="What is the current state of multimodal AI systems that combine vision and language?",
        difficulty="intermediate",
        objective="Evaluate vision-language models, multimodal architectures, training paradigms, and benchmarks.",
        expected_findings=[
            "contrastive learning",
            "cross-modal attention",
            "visual grounding",
            "zero-shot transfer",
        ],
        expected_subtopics=[
            "vision-language models",
            "multimodal architectures",
            "training data",
            "evaluation benchmarks",
        ],
        expected_references=[
            "https://arxiv.org/abs/2103.00020",
        ],
        expected_quality_score=70.0,
        tags=["ai", "multimodal", "vision-language"],
    ),
    # ── Category 2: Healthcare ──────────────────────────────────────
    BenchmarkQuestion(
        id="HC-01",
        category="Healthcare",
        query="How is artificial intelligence being applied to drug discovery and development?",
        difficulty="intermediate",
        objective="Survey AI methods for molecular design, target identification, clinical trial optimization, and regulatory considerations.",
        expected_findings=[
            "molecular docking",
            "generative chemistry",
            "DeepMind AlphaFold",
            "clinical trial prediction",
        ],
        expected_subtopics=[
            "molecular generation",
            "protein structure prediction",
            "virtual screening",
            "clinical trial optimization",
        ],
        expected_references=[
            "https://www.nature.com/articles/s41586-021-03819-2",
        ],
        expected_quality_score=75.0,
        tags=["healthcare", "drug-discovery", "ai"],
    ),
    BenchmarkQuestion(
        id="HC-02",
        category="Healthcare",
        query="What are the major challenges and opportunities in telemedicine adoption?",
        difficulty="basic",
        objective="Analyze barriers to telemedicine adoption including regulatory, technological, and equity considerations.",
        expected_findings=[
            "regulatory barriers",
            "digital divide",
            "reimbursement models",
            "patient satisfaction",
        ],
        expected_subtopics=[
            "regulatory landscape",
            "technology infrastructure",
            "health equity",
            "clinical outcomes",
        ],
        expected_quality_score=65.0,
        tags=["healthcare", "telemedicine", "digital-health"],
    ),
    BenchmarkQuestion(
        id="HC-03",
        category="Healthcare",
        query="What is the role of federated learning in privacy-preserving medical data analysis?",
        difficulty="advanced",
        objective="Evaluate federated learning architectures for healthcare, including data heterogeneity, security, and regulatory compliance.",
        expected_findings=[
            "data heterogeneity challenge",
            "differential privacy guarantees",
            "secure aggregation",
            "HIPAA compliance",
        ],
        expected_subtopics=[
            "federated architectures",
            "privacy mechanisms",
            "non-IID data",
            "regulatory frameworks",
        ],
        expected_references=[
            "https://arxiv.org/abs/2103.11865",
        ],
        expected_quality_score=70.0,
        tags=["healthcare", "federated-learning", "privacy"],
    ),
    # ── Category 3: Cybersecurity ───────────────────────────────────
    BenchmarkQuestion(
        id="CS-01",
        category="Cybersecurity",
        query="How effective are AI-powered intrusion detection systems compared to traditional signature-based methods?",
        difficulty="intermediate",
        objective="Compare ML-based and signature-based IDS approaches in terms of detection rate, false positives, and adversarial robustness.",
        expected_findings=[
            "anomaly detection",
            "false positive rates",
            "adversarial evasion",
            "behavioral analysis",
        ],
        expected_subtopics=[
            "signature-based detection",
            "ML-based detection",
            "adversarial robustness",
            "deployment challenges",
        ],
        expected_quality_score=70.0,
        tags=["cybersecurity", "intrusion-detection", "ai"],
    ),
    BenchmarkQuestion(
        id="CS-02",
        category="Cybersecurity",
        query="What are the most significant zero-day vulnerabilities discovered and disclosed in the last three years?",
        difficulty="advanced",
        objective="Survey notable zero-day vulnerabilities, exploit chains, disclosure practices, and mitigation strategies.",
        expected_findings=[
            "supply chain attacks",
            "remote code execution",
            "privilege escalation",
            "responsible disclosure",
        ],
        expected_subtopics=[
            "notable vulnerabilities",
            "exploit techniques",
            "disclosure processes",
            "mitigation strategies",
        ],
        expected_quality_score=65.0,
        tags=["cybersecurity", "zero-day", "vulnerabilities"],
    ),
    BenchmarkQuestion(
        id="CS-03",
        category="Cybersecurity",
        query="What are the emerging threats and defenses in AI system security?",
        difficulty="advanced",
        objective="Analyze adversarial ML attacks, prompt injection, model extraction, and defense mechanisms for AI systems.",
        expected_findings=[
            "adversarial examples",
            "prompt injection",
            "model extraction",
            "data poisoning",
        ],
        expected_subtopics=[
            "adversarial ML",
            "LLM security",
            "model theft",
            "defense frameworks",
        ],
        expected_references=[
            "https://arxiv.org/abs/2302.10216",
        ],
        expected_quality_score=75.0,
        tags=["cybersecurity", "ai-security", "adversarial-ml"],
    ),
    # ── Category 4: Climate & Environment ───────────────────────────
    BenchmarkQuestion(
        id="CE-01",
        category="Climate & Environment",
        query="What role does carbon capture utilization and storage play in achieving net-zero emissions?",
        difficulty="intermediate",
        objective="Evaluate CCUS technologies, cost curves, scalability, and integration with renewable energy systems.",
        expected_findings=[
            "point source capture",
            "direct air capture",
            "storage capacity",
            "economic viability",
        ],
        expected_subtopics=[
            "capture technologies",
            "utilization pathways",
            "storage geology",
            "policy frameworks",
        ],
        expected_quality_score=70.0,
        tags=["climate", "carbon-capture", "net-zero"],
    ),
    BenchmarkQuestion(
        id="CE-02",
        category="Climate & Environment",
        query="How do extreme weather events affect global supply chain resilience?",
        difficulty="basic",
        objective="Analyze the impact of climate-driven extreme weather on logistics, manufacturing, and food supply chains.",
        expected_findings=[
            "supply chain disruption",
            "manufacturing downtime",
            "agricultural impact",
            "adaptation strategies",
        ],
        expected_subtopics=[
            "weather patterns",
            "supply chain risk",
            "economic impact",
            "resilience strategies",
        ],
        expected_quality_score=65.0,
        tags=["climate", "supply-chain", "resilience"],
    ),
    # ── Category 5: Software Engineering ────────────────────────────
    BenchmarkQuestion(
        id="SE-01",
        category="Software Engineering",
        query="How do large language models change software testing and debugging practices?",
        difficulty="intermediate",
        objective="Evaluate LLM applications in test generation, bug detection, code review, and automated debugging.",
        expected_findings=[
            "test case generation",
            "bug detection",
            "automated repair",
            "code review assistance",
        ],
        expected_subtopics=[
            "test generation",
            "debugging",
            "code review",
            "limitations and risks",
        ],
        expected_quality_score=70.0,
        tags=["software-engineering", "llm", "testing"],
    ),
    BenchmarkQuestion(
        id="SE-02",
        category="Software Engineering",
        query="What are the best practices for implementing microservices architectures in production?",
        difficulty="basic",
        objective="Survey design patterns, deployment strategies, monitoring, and operational challenges for microservices.",
        expected_findings=[
            "service decomposition",
            "API gateway patterns",
            "observability",
            "deployment automation",
        ],
        expected_subtopics=[
            "architecture patterns",
            "communication",
            "monitoring",
            "deployment",
        ],
        expected_quality_score=65.0,
        tags=["software-engineering", "microservices", "architecture"],
    ),
    BenchmarkQuestion(
        id="SE-03",
        category="Software Engineering",
        query="What are the security implications of using open-source dependencies in modern software development?",
        difficulty="intermediate",
        objective="Analyze supply chain risks, dependency management strategies, vulnerability detection, and license compliance.",
        expected_findings=[
            "supply chain attacks",
            "dependency confusion",
            "SBOM management",
            "automated scanning",
        ],
        expected_subtopics=[
            "supply chain risks",
            "dependency management",
            "vulnerability scanning",
            "license compliance",
        ],
        expected_quality_score=70.0,
        tags=["software-engineering", "security", "open-source"],
    ),
    # ── Category 6: Economics & Society ─────────────────────────────
    BenchmarkQuestion(
        id="ES-01",
        category="Economics & Society",
        query="What is the economic impact of artificial intelligence on labor markets?",
        difficulty="intermediate",
        objective="Analyze job displacement, skill demand shifts, productivity effects, and policy responses to AI-driven automation.",
        expected_findings=[
            "job displacement",
            "skill polarization",
            "productivity gains",
            "reskilling needs",
        ],
        expected_subtopics=[
            "automation impact",
            "skill shifts",
            "productivity",
            "policy responses",
        ],
        expected_quality_score=70.0,
        tags=["economics", "ai", "labor-markets"],
    ),
    BenchmarkQuestion(
        id="ES-02",
        category="Economics & Society",
        query="How does digital platform regulation affect innovation and competition?",
        difficulty="advanced",
        objective="Evaluate the impact of regulations like DMA, DSA, and antitrust actions on platform ecosystems and startup innovation.",
        expected_findings=[
            "market concentration",
            "innovation trade-offs",
            "compliance costs",
            "regulatory fragmentation",
        ],
        expected_subtopics=[
            "platform regulation",
            "antitrust",
            "innovation impact",
            "global divergence",
        ],
        expected_quality_score=65.0,
        tags=["economics", "regulation", "platforms"],
    ),
    # ── Category 7: Education ───────────────────────────────────────
    BenchmarkQuestion(
        id="ED-01",
        category="Education",
        query="What is the effectiveness of adaptive learning technologies in personalized education?",
        difficulty="basic",
        objective="Survey adaptive learning systems, personalization algorithms, efficacy studies, and implementation challenges.",
        expected_findings=[
            "knowledge tracing",
            "adaptive pathways",
            "learning analytics",
            "efficacy evidence",
        ],
        expected_subtopics=[
            "adaptive systems",
            "personalization",
            "assessment",
            "implementation barriers",
        ],
        expected_quality_score=65.0,
        tags=["education", "adaptive-learning", "personalized-learning"],
    ),
    BenchmarkQuestion(
        id="ED-02",
        category="Education",
        query="How are large language models being used in educational contexts and what are the risks?",
        difficulty="intermediate",
        objective="Evaluate LLM applications in tutoring, assessment, content creation, and the risks of plagiarism and misinformation.",
        expected_findings=[
            "AI tutoring",
            "automated assessment",
            "plagiarism concerns",
            "equity gaps",
        ],
        expected_subtopics=[
            "tutoring applications",
            "assessment tools",
            "academic integrity",
            "equity and access",
        ],
        expected_quality_score=70.0,
        tags=["education", "llm", "ai-in-education"],
    ),
    BenchmarkQuestion(
        id="ED-03",
        category="Education",
        query="What evidence exists for the effectiveness of gamification in higher education?",
        difficulty="basic",
        objective="Analyze empirical studies on gamification elements, engagement metrics, learning outcomes, and long-term retention.",
        expected_findings=[
            "engagement improvement",
            "motivation effects",
            "learning outcomes",
            "design principles",
        ],
        expected_subtopics=[
            "gamification elements",
            "empirical evidence",
            "motivation theory",
            "implementation",
        ],
        expected_quality_score=65.0,
        tags=["education", "gamification", "engagement"],
    ),
]


def get_questions_by_category() -> dict[str, list[BenchmarkQuestion]]:
    categories: dict[str, list[BenchmarkQuestion]] = {}
    for q in BENCHMARK_20_QUESTIONS:
        categories.setdefault(q.category, []).append(q)
    return categories


def get_questions_by_difficulty() -> dict[str, list[BenchmarkQuestion]]:
    levels: dict[str, list[BenchmarkQuestion]] = {}
    for q in BENCHMARK_20_QUESTIONS:
        levels.setdefault(q.difficulty, []).append(q)
    return levels


def get_questions_by_tag(tag: str) -> list[BenchmarkQuestion]:
    return [q for q in BENCHMARK_20_QUESTIONS if tag in q.tags]


BENCHMARK_CATEGORIES = [
    "Artificial Intelligence",
    "Healthcare",
    "Cybersecurity",
    "Climate & Environment",
    "Software Engineering",
    "Economics & Society",
    "Education",
]

BENCHMARK_DIFFICULTY_DISTRIBUTION = {
    "basic": 5,
    "intermediate": 10,
    "advanced": 5,
}
