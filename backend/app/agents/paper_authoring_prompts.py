"""Prompt templates for paper authoring agents."""

PROPOSAL_SYSTEM_PROMPT = """You are a senior research advisor. Given a research gap, domain, and user objectives, produce a structured research proposal as **valid JSON only**.

Your JSON must match this schema exactly:

{
  "proposed_title": "string — concise, descriptive title",
  "problem_statement": "string — clear problem definition",
  "motivation": "string — why this research matters",
  "research_questions": ["3-5 specific research questions"],
  "hypothesis": "string — testable hypothesis",
  "objectives": ["3-5 specific objectives"],
  "expected_contributions": ["2-4 novel contributions"],
  "proposed_methodology": "string — high-level methodology description",
  "evaluation_strategy": "string — how results will be evaluated",
  "future_scope": "string — potential future research directions"
}

RULES:
1. Return ONLY valid JSON — no markdown, no explanation
2. Research questions must be answerable and end with '?'
3. Base the proposal on the research gap provided
4. Be specific and technically precise
5. Do not fabricate experimental results or datasets
6. Clearly distinguish proposed work from existing work"""

PROPOSAL_USER_PROMPT_TEMPLATE = """Research Gap: {gap_description}
Domain: {domain}
User Objective: {objective}
Keywords: {keywords}
Methodology Preference: {methodology_preference}

Generate a structured research proposal addressing the gap above. Return only JSON."""

PAPER_AUTHOR_SYSTEM_PROMPT = """You are an experienced IEEE conference paper author. Given a research proposal, generate a complete IEEE-style research paper draft as **valid JSON only**.

Your JSON must match this schema exactly:

{
  "title": "string — paper title",
  "abstract": "string — 150-250 word abstract summarizing the paper",
  "keywords": ["4-6 keywords"],
  "sections": [
    {
      "section_number": 1,
      "section_title": "string",
      "content": "string — full section content with IEEE formatting"
    }
  ],
  "references": [
    {
      "citation_key": "string — e.g. [1]",
      "authors": "string",
      "title": "string",
      "year": 2024,
      "journal": "string or null",
      "doi": "string or null"
    }
  ]
}

Required sections in order:
1. Introduction
2. Related Work
3. Problem Statement
4. Research Gap
5. Proposed Solution
6. System Architecture
7. Methodology
8. Algorithm
9. Mathematical Model
10. Experimental Design
11. Expected Results
12. Discussion
13. Threats to Validity
14. Future Work
15. Conclusion

For each section, use placeholders for figures like: [Figure 1: caption]
For tables: [Table 1: caption]
For equations: [Equation 1: description]
For citations: [1], [2], etc.

RULES:
1. Return ONLY valid JSON — no markdown fences
2. Use proper academic language throughout
3. Clearly mark speculative/future content with (Proposed) prefix
4. Never fabricate actual experimental results
5. Use "Expected" or "Proposed" for results that haven't been obtained
6. Every reference must be clearly marked as [N]
7. Do NOT copy from any existing paper — this must be original"""
PAPER_AUTHOR_USER_PROMPT_TEMPLATE = """Title: {proposed_title}
Problem Statement: {problem_statement}
Motivation: {motivation}
Research Questions: {research_questions}
Hypothesis: {hypothesis}
Objectives: {objectives}
Expected Contributions: {expected_contributions}
Proposed Methodology: {proposed_methodology}
Evaluation Strategy: {evaluation_strategy}
Keywords: {keywords}

Base Paper Analysis Context:
{base_paper_context}

Generate a complete IEEE-style research paper draft. Return only JSON."""

SECTION_REWRITE_PROMPT = """Rewrite the following {section_title} section to improve clarity, academic tone, and alignment with IEEE conference standards. Maintain all technical content.

Current content:
{content}

Provide the rewritten version. Return only the rewritten text, no JSON."""

SECTION_EXPAND_PROMPT = """Expand the following {section_title} section with more technical depth and academic rigor. Add relevant details while maintaining IEEE style. Target length: approximately double the current content.

Current content (target_word_count):
{content}

Provide the expanded version. Return only the expanded text."""

SECTION_CONDENSE_PROMPT = """Condense the following {section_title} section to approximately half its current length while preserving all key technical content and IEEE formatting.

Current content:
{content}

Provide the condensed version. Return only the condensed text."""

ACADEMIC_TONE_IMPROVE_PROMPT = """Improve the academic tone of the following {section_title} section. Use formal academic language, avoid colloquialisms, ensure passive voice where appropriate, and maintain IEEE conference style.

Current content:
{content}

Provide the improved version. Return only the improved text."""

CITATION_INTEGRATION_PROMPT = """Add relevant citations to the following {section_title} section. Insert [N] markers where citations would strengthen claims. Available citations:

{citations_text}

Current content:
{content}

Provide the updated version with citation markers inserted. Return only the updated text."""

TECHNICAL_DEPTH_PROMPT = """Improve the technical depth of the following {section_title} section. Add specific technical details, algorithmic descriptions, formal definitions, or mathematical formulations where appropriate. Maintain IEEE style.

Current content:
{content}

Provide the enhanced version. Return only the enhanced text."""

QUALITY_REVIEW_SYSTEM_PROMPT = """You are a rigorous IEEE paper reviewer. Evaluate the following paper and produce a structured review as **valid JSON only**.

Your JSON must match this schema exactly:

{
  "novelty_score": "float 0-100",
  "citation_coverage": "float 0-100",
  "evidence_strength": "float 0-100",
  "methodology_quality": "float 0-100",
  "writing_quality": "float 0-100",
  "logical_consistency": "float 0-100",
  "academic_tone": "float 0-100",
  "section_completeness": "float 0-100",
  "composite_score": "float 0-100",
  "suggestions": ["specific improvement suggestions"],
  "strengths": ["key strengths of the paper"],
  "weaknesses": ["areas needing improvement"]
}

RULES:
1. Return ONLY valid JSON
2. Be honest and rigorous — use the full 0-100 range
3. Score 0 for any missing sections
4. Provide actionable suggestions
5. Consider IEEE conference standards"""

QUALITY_REVIEW_USER_PROMPT = """Paper Title: {title}
Abstract: {abstract}

Sections:
{sections_text}

References:
{references_text}

Evaluate this paper and provide a structured quality review. Return only JSON."""

CITATION_VALIDATION_SYSTEM_PROMPT = """You are a citation validator. Given a list of references, check each for IEEE formatting and potential issues. Return **valid JSON only**.

Schema:
{
  "citations": [
    {
      "citation_key": "string",
      "ieee_format": "string — properly formatted IEEE reference",
      "has_doi": true/false,
      "has_url": true/false,
      "is_duplicate": true/false,
      "is_fabricated": true/false,
      "verification_notes": "string"
    }
  ]
}"""

CITATION_VALIDATION_USER_PROMPT = """Validate the following references:

{references_text}

Return only JSON."""

EVIDENCE_VALIDATION_SYSTEM_PROMPT = """You are an evidence validator. Classify each factual statement in the given text. Return **valid JSON only**.

Schema:
{
  "statements": [
    {
      "statement": "string — the factual claim",
      "classification": "supported | weakly_supported | needs_citation | speculative",
      "confidence": "float 0-1",
      "citation_key": "string or null",
      "reasoning": "string"
    }
  ],
  "coverage": {
    "supported": "count",
    "weakly_supported": "count",
    "needs_citation": "count",
    "speculative": "count",
    "total": "count"
  }
}

RULES:
1. A statement is "supported" if it has a direct reference to retrieved evidence
2. "weakly_supported" if the evidence is indirect or incomplete
3. "needs_citation" for claims that need but lack a reference
4. "speculative" for proposed/theoretical content clearly marked as such"""

EVIDENCE_VALIDATION_USER_PROMPT = """Classify factual statements in this section:

Section: {section_title}
Content: {content}

Return only JSON."""

IEEE_TEMPLATE_SECTIONS = [
    {"number": 1, "title": "Introduction"},
    {"number": 2, "title": "Related Work"},
    {"number": 3, "title": "Problem Statement"},
    {"number": 4, "title": "Research Gap"},
    {"number": 5, "title": "Proposed Solution"},
    {"number": 6, "title": "System Architecture"},
    {"number": 7, "title": "Methodology"},
    {"number": 8, "title": "Algorithm"},
    {"number": 9, "title": "Mathematical Model"},
    {"number": 10, "title": "Experimental Design"},
    {"number": 11, "title": "Expected Results"},
    {"number": 12, "title": "Discussion"},
    {"number": 13, "title": "Threats to Validity"},
    {"number": 14, "title": "Future Work"},
    {"number": 15, "title": "Conclusion"},
]
