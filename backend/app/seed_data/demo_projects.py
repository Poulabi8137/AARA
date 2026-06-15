"""10 polished showcase projects for public demo and portfolio presentation.

Each project includes a research query, expected quality score, and
seed report data that demonstrates AARA's research capabilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DEMO_PROJECTS: list[dict[str, Any]] = [
    {
        "title": "AI Ethics and Transparency in Healthcare Decision-Making",
        "description": "A comprehensive analysis of ethical frameworks, regulatory requirements, and technical approaches for deploying transparent AI systems in clinical settings. Covers GDPR compliance, explainability methods, bias detection, and accountability frameworks.",
        "category": "Artificial Intelligence",
        "difficulty": "advanced",
        "query": "Ethical considerations in AI transparency and explainability for healthcare applications",
        "tags": ["ai-ethics", "healthcare", "transparency", "explainability"],
        "expected_subtopics": [
            "Explainable AI (XAI) Methods",
            "Regulatory Frameworks (GDPR, HIPAA)",
            "Bias Detection and Mitigation",
            "Clinical Deployment Challenges",
            "Accountability and Governance",
        ],
        "expected_quality_score": 85,
        "seed_report_summary": (
            "This report investigates ethical frameworks for transparent AI in healthcare, "
            "covering XAI methods (LIME, SHAP, attention mechanisms), regulatory compliance "
            "under GDPR and HIPAA, bias detection across demographic groups, and governance "
            "frameworks for accountable AI deployment."
        ),
    },
    {
        "title": "Quantum Machine Learning: Algorithms, Hardware, and Applications",
        "description": "Survey of quantum machine learning algorithms including variational circuits, quantum kernel methods, and quantum neural networks. Analysis of NISQ-era hardware limitations, error mitigation strategies, and potential quantum advantage in optimization and chemistry.",
        "category": "Quantum Computing",
        "difficulty": "advanced",
        "query": "Quantum machine learning algorithms and their potential for practical quantum advantage",
        "tags": ["quantum", "machine-learning", "algorithms"],
        "expected_subtopics": [
            "Variational Quantum Algorithms",
            "Quantum Kernel Methods",
            "Quantum Neural Networks",
            "NISQ Hardware Limitations",
            "Error Mitigation Techniques",
        ],
        "expected_quality_score": 80,
        "seed_report_summary": (
            "A thorough survey of quantum ML algorithms, analyzing variational circuits, "
            "quantum kernel methods, and hybrid classical-quantum approaches. Evaluates NISQ "
            "hardware constraints, error mitigation strategies, and identifies chemistry "
            "optimization as the most promising near-term application."
        ),
    },
    {
        "title": "Federated Learning and Differential Privacy for Distributed Healthcare Data",
        "description": "Analysis of privacy-preserving machine learning techniques for healthcare, including federated learning architectures, differential privacy guarantees, secure aggregation protocols, and regulatory compliance with patient data protection laws.",
        "category": "Privacy & Security",
        "difficulty": "intermediate",
        "query": "Privacy-preserving machine learning for healthcare: federated learning and differential privacy approaches",
        "tags": ["federated-learning", "privacy", "healthcare", "differential-privacy"],
        "expected_subtopics": [
            "Federated Learning Architectures",
            "Differential Privacy Mechanisms",
            "Secure Aggregation Protocols",
            "Non-IID Data Challenges",
            "Regulatory Compliance (HIPAA, GDPR)",
        ],
        "expected_quality_score": 82,
        "seed_report_summary": (
            "Evaluates federated learning architectures and differential privacy guarantees "
            "for privacy-preserving healthcare ML. Identifies secure aggregation and gradient "
            "compression as critical components, with non-IID data distribution being the "
            "primary technical challenge in hospital collaborations."
        ),
    },
    {
        "title": "Direct Air Capture: Technology Readiness and Economic Viability",
        "description": "Evaluation of direct air capture (DAC) technologies for atmospheric CO2 removal, including sorbent-based and solvent-based systems, energy requirements, cost analysis, and integration with carbon utilization and storage infrastructure.",
        "category": "Climate Science",
        "difficulty": "intermediate",
        "query": "Direct air capture technologies for climate change mitigation: technological readiness and economic viability",
        "tags": ["climate", "carbon-capture", "dac", "clean-energy"],
        "expected_subtopics": [
            "DAC Technologies Overview",
            "Energy Requirements Analysis",
            "Cost Projections and Scalability",
            "Integration with Storage",
            "Policy and Market Frameworks",
        ],
        "expected_quality_score": 78,
        "seed_report_summary": (
            "Comprehensive evaluation of direct air capture technologies, analyzing solid "
            "sorbent and liquid solvent systems. Finds current costs of $250-600/tCO2 with "
            "projections to $100-150/tCO2 by 2035. Energy requirements and geological storage "
            "capacity are identified as critical scaling factors."
        ),
    },
    {
        "title": "Low-Resource NLP: Transfer Learning and Cross-Lingual Methods",
        "description": "Survey of techniques for natural language processing in languages with limited annotated data, including multilingual transfer learning, data augmentation, cross-lingual model architectures, and evaluation methodologies for low-resource scenarios.",
        "category": "Natural Language Processing",
        "difficulty": "intermediate",
        "query": "Low-resource natural language processing: transfer learning and cross-lingual methods",
        "tags": ["nlp", "low-resource", "transfer-learning", "cross-lingual"],
        "expected_subtopics": [
            "Multilingual Transfer Learning",
            "Cross-Lingual Model Architectures",
            "Data Augmentation Strategies",
            "Few-Shot and Zero-Shot Methods",
            "Evaluation Benchmarks",
        ],
        "expected_quality_score": 80,
        "seed_report_summary": (
            "Analyzes transfer learning and cross-lingual methods for low-resource NLP. "
            "Finds that multilingual pre-training (mBERT, XLM-R) combined with data "
            "augmentation achieves strong zero-shot transfer, while few-shot fine-tuning "
            "with target-language data remains essential for domain-specific tasks."
        ),
    },
    {
        "title": "Adversarial Robustness in Deep Learning Systems",
        "description": "Comprehensive analysis of adversarial attacks and defenses in deep learning, including gradient-based attacks, certified defenses, adversarial training, and robustness evaluation. Covers computer vision, NLP, and multimodal systems.",
        "category": "Artificial Intelligence",
        "difficulty": "advanced",
        "query": "Adversarial robustness in deep learning: attacks, defenses, and evaluation",
        "tags": ["ai", "adversarial", "robustness", "security"],
        "expected_subtopics": [
            "Adversarial Attack Methods",
            "Certified Defenses",
            "Adversarial Training",
            "Robustness Evaluation",
            "Real-World Implications",
        ],
        "expected_quality_score": 82,
        "seed_report_summary": (
            "Deep dive into adversarial ML, covering white-box and black-box attacks, "
            "certified defenses (randomized smoothing, interval bound propagation), "
            "adversarial training variants, and the robustness-accuracy trade-off. "
            "Identifies evaluation standardization as a critical open challenge."
        ),
    },
    {
        "title": "Large Language Models for Code Generation and Software Engineering",
        "description": "Analysis of LLM applications in software engineering including code generation, debugging, testing, code review, and documentation. Evaluates models (GPT-4, Claude, CodeLlama), benchmarks (HumanEval, SWE-bench), and practical adoption patterns.",
        "category": "Software Engineering",
        "difficulty": "intermediate",
        "query": "How large language models are transforming software engineering practices",
        "tags": ["llm", "software-engineering", "code-generation", "ai"],
        "expected_subtopics": [
            "Code Generation Capabilities",
            "Automated Debugging and Repair",
            "Test Generation",
            "Code Review Automation",
            "Adoption Patterns and Risks",
        ],
        "expected_quality_score": 80,
        "seed_report_summary": (
            "Evaluates LLM applications across the software development lifecycle. Finds "
            "strong performance in code generation and test creation, emerging capabilities "
            "in automated debugging, and significant risks including hallucinated code, "
            "security vulnerabilities, and over-reliance on AI-generated output."
        ),
    },
    {
        "title": "Climate Risk Assessment for Global Supply Chains",
        "description": "Analysis of climate change impacts on global supply chains, including physical risk from extreme weather, transition risk from policy changes, and adaptation strategies. Covers risk modeling, scenario analysis, and resilience planning frameworks.",
        "category": "Climate Science",
        "difficulty": "basic",
        "query": "Climate change risks to global supply chains: assessment and adaptation strategies",
        "tags": ["climate", "supply-chain", "risk-assessment"],
        "expected_subtopics": [
            "Physical Climate Risks",
            "Transition Risks",
            "Risk Modeling Approaches",
            "Adaptation Strategies",
            "Regulatory Disclosure",
        ],
        "expected_quality_score": 75,
        "seed_report_summary": (
            "Assesses climate-related risks across global supply chains, identifying extreme "
            "weather disruption and carbon policy transition as primary risk categories. "
            "Recommends scenario-based risk modeling, supplier diversification, and "
            "TCFD-aligned disclosure frameworks for resilience planning."
        ),
    },
    {
        "title": "AI-Driven Drug Discovery: Methods, Successes, and Limitations",
        "description": "Survey of artificial intelligence applications in drug discovery, including molecular generation, protein structure prediction, virtual screening, clinical trial optimization, and analysis of approved AI-discovered drugs and pipeline candidates.",
        "category": "Healthcare",
        "difficulty": "intermediate",
        "query": "Artificial intelligence in drug discovery: current methods and real-world impact",
        "tags": ["healthcare", "drug-discovery", "ai", "biotech"],
        "expected_subtopics": [
            "Molecular Generation Methods",
            "Protein Structure Prediction (AlphaFold)",
            "Virtual Screening",
            "Clinical Trial Optimization",
            "Approved and Pipeline Drugs",
        ],
        "expected_quality_score": 78,
        "seed_report_summary": (
            "Comprehensive survey of AI in drug discovery, covering generative chemistry, "
            "AlphaFold-driven structure prediction, and ML-optimized clinical trials. "
            "Identifies the Antibody-Drug Conjugate space and target identification "
            "as areas of highest AI impact, while noting the reproducibility crisis "
            "in computational chemistry studies."
        ),
    },
    {
        "title": "Economic Impacts of AI Automation on Global Labor Markets",
        "description": "Analysis of AI-driven automation effects on employment, wage polarization, skill demand shifts, and productivity growth. Examines historical automation parallels, sector-specific impacts, and policy responses including universal basic income and reskilling programs.",
        "category": "Economics & Society",
        "difficulty": "intermediate",
        "query": "Economic impact of artificial intelligence on labor markets and employment",
        "tags": ["economics", "ai", "labor", "automation", "policy"],
        "expected_subtopics": [
            "Automation and Job Displacement",
            "Skill Demand Polarization",
            "Productivity Effects",
            "Sector-Specific Analysis",
            "Policy Responses (UBI, Reskilling)",
        ],
        "expected_quality_score": 80,
        "seed_report_summary": (
            "Analyzes AI's impact on labor markets, finding significant job transformation "
            "rather than mass displacement. Knowledge worker roles face the most disruption, "
            "while physical and creative roles show different exposure patterns. Productivity "
            "gains are concentrated in early-adopting firms, widening inter-firm inequality. "
            "Recommends portable benefits, lifelong learning infrastructure, and AI literacy "
            "programs as essential policy responses."
        ),
    },
]

DEMO_CATEGORIES = sorted(set(p["category"] for p in DEMO_PROJECTS))

DEMO_TAGS = sorted(set(tag for p in DEMO_PROJECTS for tag in p["tags"]))

DEMO_STATS = {
    "total_projects": len(DEMO_PROJECTS),
    "categories": len(DEMO_CATEGORIES),
    "unique_tags": len(DEMO_TAGS),
    "avg_expected_quality": round(sum(p["expected_quality_score"] for p in DEMO_PROJECTS) / len(DEMO_PROJECTS), 1),
    "highest_quality": max(p["expected_quality_score"] for p in DEMO_PROJECTS),
    "lowest_quality": min(p["expected_quality_score"] for p in DEMO_PROJECTS),
    "difficulty_distribution": {
        "basic": sum(1 for p in DEMO_PROJECTS if p["difficulty"] == "basic"),
        "intermediate": sum(1 for p in DEMO_PROJECTS if p["difficulty"] == "intermediate"),
        "advanced": sum(1 for p in DEMO_PROJECTS if p["difficulty"] == "advanced"),
    },
}
