"""Comprehensive benchmark execution: run all queries, save outputs, generate reports."""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from app.llm.mock_provider import MockProvider
from app.agents.planner_agent import PlannerAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.gap_detection_agent import GapDetectionAgent
from app.agents.report_generator_agent import ReportGeneratorAgent
from app.agents.state import ResearchState

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "benchmark_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def run_single(query: str) -> dict[str, Any]:
    llm = MockProvider()
    state = ResearchState(query=query)

    # Planner
    t0 = time.monotonic()
    agent = PlannerAgent(llm_provider=llm)
    state = await agent.arun(state)

    if not state.get("retrieved_documents"):
        state["retrieved_documents"] = [
            {"subtopic": "general", "evidence": [], "sources": []}
        ]

    # Summarizer
    agent = SummarizerAgent(llm_provider=llm)
    state = await agent.arun(state)

    # Gap Detection
    agent = GapDetectionAgent(llm_provider=llm)
    state = await agent.arun(state)

    # Report Generator
    agent = ReportGeneratorAgent(llm_provider=llm)
    state = await agent.arun(state)

    elapsed = time.monotonic() - t0
    report = state.get("generated_report", "")

    return {
        "query": query,
        "status": state.get("status", "unknown"),
        "elapsed": round(elapsed, 3),
        "report_length": len(report),
        "report_preview": report[:500],
        "agent_metrics": state.get("agent_metrics", {}),
    }


async def main():
    benchmarks = [
        # Builtin 3
        "What are the key challenges in AI safety research?",
        "What is the current state of quantum computing error correction?",
        "What are the impacts of climate change on global food security?",
        # AI
        "Ethical considerations in AI transparency and explainability for healthcare applications",
        "How do transformer architectures compare to state space models for long-context sequence modeling?",
        "What methods exist for detecting and mitigating bias in machine learning models?",
        # Healthcare
        "How is artificial intelligence being applied to drug discovery and development?",
        "What are the major challenges and opportunities in telemedicine adoption?",
        # Cybersecurity
        "How effective are AI-powered intrusion detection systems compared to traditional signature-based methods?",
        # Climate
        "What role does carbon capture utilization and storage play in achieving net-zero emissions?",
        # Software Engineering
        "How do large language models change software testing and debugging practices?",
        # Economics
        "What is the economic impact of artificial intelligence on labor markets?",
        # Education
        "What is the effectiveness of adaptive learning technologies in personalized education?",
    ]

    showcases = [
        "AI Ethics and Transparency in Healthcare Decision-Making",
        "Quantum Machine Learning: Algorithms, Hardware, and Applications",
        "Federated Learning and Differential Privacy for Distributed Healthcare Data",
        "Direct Air Capture: Technology Readiness and Economic Viability",
        "Adversarial Robustness in Deep Learning Systems",
        "Large Language Models for Code Generation and Software Engineering",
        "Climate Risk Assessment for Global Supply Chains",
        "AI-Driven Drug Discovery: Methods, Successes, and Limitations",
        "Low-Resource NLP: Transfer Learning and Cross-Lingual Methods",
        "Economic Impacts of AI Automation on Global Labor Markets",
    ]

    all_results = {"benchmarks": [], "showcases": [], "timestamp": datetime.now(timezone.utc).isoformat()}

    print("=== RUNNING BENCHMARK SUITE ===")
    for q in benchmarks:
        print(f"  [{len([r for r in all_results['benchmarks'] if r.get('status') == 'report_generation_complete'])+1}/{len(benchmarks)}] {q[:60]}...", end=" ")
        try:
            result = await run_single(q)
            all_results["benchmarks"].append(result)
            print(f"{result['status']} ({result['report_length']} chars, {result['elapsed']}s)")
        except Exception as e:
            print(f"FAILED: {e}")
            all_results["benchmarks"].append({"query": q, "status": f"failed: {e}", "elapsed": 0, "report_length": 0})

    print("\n=== RUNNING SHOWCASE SUITE ===")
    for q in showcases:
        print(f"  [{len([r for r in all_results['showcases'] if r.get('status') == 'report_generation_complete'])+1}/{len(showcases)}] {q[:60]}...", end=" ")
        try:
            result = await run_single(q)
            all_results["showcases"].append(result)
            print(f"{result['status']} ({result['report_length']} chars, {result['elapsed']}s)")
        except Exception as e:
            print(f"FAILED: {e}")
            all_results["showcases"].append({"query": q, "status": f"failed: {e}", "elapsed": 0, "report_length": 0})

    output_path = os.path.join(OUTPUT_DIR, "all_results.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved: {output_path}")

    # Summary
    bench_ok = [r for r in all_results["benchmarks"] if r.get("status") == "report_generation_complete"]
    show_ok = [r for r in all_results["showcases"] if r.get("status") == "report_generation_complete"]
    print(f"\n=== FINAL SUMMARY ===")
    print(f"  Benchmarks: {len(bench_ok)}/{len(benchmarks)} passed")
    print(f"  Showcases:  {len(show_ok)}/{len(showcases)} passed")
    if bench_ok:
        print(f"  Avg benchmark report: {sum(r['report_length'] for r in bench_ok)//max(len(bench_ok),1)} chars")
        print(f"  Avg benchmark time:   {sum(r['elapsed'] for r in bench_ok)/max(len(bench_ok),1):.2f}s")
    if show_ok:
        print(f"  Avg showcase report:  {sum(r['report_length'] for r in show_ok)//max(len(show_ok),1)} chars")
        print(f"  Avg showcase time:    {sum(r['elapsed'] for r in show_ok)/max(len(show_ok),1):.2f}s")
    total_ok = len(bench_ok) + len(show_ok)
    total_all = len(benchmarks) + len(showcases)
    print(f"  TOTAL: {total_ok}/{total_all} succeeded ({(total_ok/total_all)*100:.0f}%)")


if __name__ == "__main__":
    asyncio.run(main())
