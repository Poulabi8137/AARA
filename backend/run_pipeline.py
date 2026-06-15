"""Run full agent pipeline end-to-end for benchmark execution."""
from __future__ import annotations

import asyncio
import json
import time

from app.llm.mock_provider import MockProvider
from app.agents.planner_agent import PlannerAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.gap_detection_agent import GapDetectionAgent
from app.agents.report_generator_agent import ReportGeneratorAgent
from app.agents.state import ResearchState


async def run_full_pipeline(query: str) -> ResearchState:
    llm = MockProvider()
    state = ResearchState(query=query)

    # Planner
    t0 = time.monotonic()
    print(f"  [Planner] Starting...")
    agent = PlannerAgent(llm_provider=llm)
    state = await agent.arun(state)
    print(f"  [Planner] Done ({time.monotonic()-t0:.1f}s)")

    # Ensure retrieved_documents exists for Summarizer
    if not state.get("retrieved_documents"):
        state["retrieved_documents"] = [
            {"subtopic": "general", "evidence": [], "sources": []}
        ]

    # Summarizer
    t0 = time.monotonic()
    print(f"  [Summarizer] Starting...")
    agent = SummarizerAgent(llm_provider=llm)
    state = await agent.arun(state)
    print(f"  [Summarizer] Done ({time.monotonic()-t0:.1f}s)")

    from app.agents.gap_detection_agent import GapDetectionAgent
    # Gap Analyzer
    t0 = time.monotonic()
    print(f"  [GapDetection] Starting...")
    agent = GapDetectionAgent(llm_provider=llm)
    state = await agent.arun(state)
    print(f"  [GapDetection] Done ({time.monotonic()-t0:.1f}s)")

    # Report Generator
    t0 = time.monotonic()
    print(f"  [ReportGenerator] Starting...")
    agent = ReportGeneratorAgent(llm_provider=llm)
    state = await agent.arun(state)
    print(f"  [ReportGenerator] Done ({time.monotonic()-t0:.1f}s)")

    report = state.get("generated_report", "")
    report_ascii = report.encode("ascii", "replace").decode("ascii")
    print(f"  Report length: {len(report)} chars")
    print(f"  Status: {state.get('status', 'unknown')}")
    print(f"  Preview: {report_ascii[:200]}...")

    return state


async def run_all_benchmarks():
    """Run all 20 benchmark + 10 showcase queries."""
    queries = [
        # 3 builtin benchmarks
        "What are the key challenges in AI safety research?",
        "What is the current state of quantum computing error correction?",
        "What are the impacts of climate change on global food security?",
        # Additional test queries
        "Ethical considerations in AI transparency and explainability for healthcare applications",
        "How do transformer architectures compare to state space models for long-context sequence modeling?",
        "What methods exist for detecting and mitigating bias in machine learning models?",
        "How is artificial intelligence being applied to drug discovery and development?",
        "What are the major challenges and opportunities in telemedicine adoption?",
        "How effective are AI-powered intrusion detection systems compared to traditional signature-based methods?",
        "What role does carbon capture utilization and storage play in achieving net-zero emissions?",
        "How do large language models change software testing and debugging practices?",
        "What is the economic impact of artificial intelligence on labor markets?",
        "What is the effectiveness of adaptive learning technologies in personalized education?",
    ]
    results = []
    for q in queries:
        print(f"\n{'='*60}")
        print(f"BENCHMARK: {q[:70]}")
        print(f"{'='*60}")
        try:
            t0 = time.monotonic()
            state = await run_full_pipeline(q)
            elapsed = time.monotonic() - t0
            results.append({
                "query": q,
                "status": state.get("status"),
                "report_length": len(state.get("generated_report", "")),
                "elapsed": round(elapsed, 2),
            })
            print(f"  RESULT: {state.get('status')} ({elapsed:.1f}s, {len(state.get('generated_report', ''))} chars)")
        except Exception as e:
            import traceback
            print(f"  FAILED: {e}")
            traceback.print_exc()
            results.append({"query": q, "status": "failed", "error": str(e), "elapsed": 0})

    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY:")
    passed = [r for r in results if r.get("status") == "report_generation_complete"]
    print(f"  Passed: {len(passed)}/{len(results)}")
    print(f"  Avg report length: {sum(r.get('report_length', 0) for r in passed)/max(len(passed),1):.0f} chars")
    print(f"  Avg execution time: {sum(r.get('elapsed', 0) for r in results)/max(len(results),1):.1f}s")
    print(f"{'='*60}")
    return results


async def main():
    results = await run_all_benchmarks()
    # Print failures
    failures = [r for r in results if r.get("status") != "report_generation_complete"]
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f.get('query', '?')[:60]}: {f.get('status', f.get('error', 'unknown'))}")


if __name__ == "__main__":
    asyncio.run(main())
