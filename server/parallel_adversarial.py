#!/usr/bin/env python3

"""
Parallel Adversarial Testing System

This module handles running multiple adversarial agents in parallel with different topic focuses.
"""

import os
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
from adversarial_agent import AdversarialAgent, AdversarialReport
from report_generator import ReportGenerator

# Topic focuses for different agents to explore different areas
TOPIC_FOCUSES = [
    "policies, terms, and conditions",
    "pricing, costs, and financial details",
    "procedures, processes, and workflows",
    "contact information and support details",
    "coverage, benefits, and exclusions",
    "deadlines, timelines, and time-sensitive information",
    "edge cases and exceptions",
    "comparisons and rankings",
    "specific numbers, dates, and metrics",
    "interpretations and opinions"
]


def extract_host_port_from_url(websocket_url: str) -> tuple[str, int]:
    """Extract host and port from websocket URL"""
    parsed = urlparse(websocket_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    return host, port


async def run_single_agent(
    websocket_base_url: str,
    duration_minutes: float,
    topic_focus: Optional[str],
    session_id: str,
    adversarial_model: str,
    judge_model: str
) -> AdversarialReport:
    """Run a single adversarial agent"""
    # Construct websocket URL with session_id
    # websocket_base_url should be like "ws://localhost:8000/ws" or "ws://localhost:8000"
    if websocket_base_url.endswith("/ws"):
        websocket_url = f"{websocket_base_url}/{session_id}"
    elif websocket_base_url.endswith("/"):
        websocket_url = f"{websocket_base_url}ws/{session_id}"
    else:
        websocket_url = f"{websocket_base_url}/ws/{session_id}"
    
    host, port = extract_host_port_from_url(websocket_url)
    
    agent = AdversarialAgent(
        adversarial_model=adversarial_model,
        judge_model=judge_model,
        agent_host=host,
        agent_port=port,
        session_id=session_id,
        topic_focus=topic_focus,
        websocket_url=websocket_url
    )
    
    report = await agent.run_adversarial_test(duration_minutes=duration_minutes)
    return report


async def run_parallel_adversarial(
    websocket_base_url: str,
    parallel_executions: int,
    duration_minutes: float,
    adversarial_model: Optional[str] = None,
    judge_model: Optional[str] = None,
    group_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run multiple adversarial agents in parallel with different topic focuses.
    
    Args:
        websocket_base_url: Base WebSocket URL (e.g., "ws://localhost:8000" or "ws://localhost:8000/ws")
        parallel_executions: Number of parallel agents to run
        duration_minutes: Duration of test in minutes
        adversarial_model: Model for adversarial queries (optional)
        judge_model: Model for analysis (optional)
        group_id: Group identifier (optional, auto-generated if not provided)
    
    Returns:
        Dictionary with session_ids and group_id
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    adversarial_model = adversarial_model or os.getenv("ADVERSARIAL_MODEL", "openai/gpt-4o")
    judge_model = judge_model or os.getenv("JUDGE_MODEL", "openai/gpt-4o")
    group_id = group_id or f"grp-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # Generate session IDs
    session_ids = []
    for i in range(parallel_executions):
        session_id = f"{group_id}-agent-{i+1}"
        session_ids.append(session_id)
    
    # Assign topic focuses (cycle through if we have more agents than topics)
    topic_assignments = []
    for i in range(parallel_executions):
        topic_focus = TOPIC_FOCUSES[i % len(TOPIC_FOCUSES)]
        topic_assignments.append(topic_focus)
    
    # Run all agents in parallel
    tasks = [
        run_single_agent(
            websocket_base_url=websocket_base_url,
            duration_minutes=duration_minutes,
            topic_focus=topic_assignments[i],
            session_id=session_ids[i],
            adversarial_model=adversarial_model,
            judge_model=judge_model
        )
        for i in range(parallel_executions)
    ]
    
    reports = await asyncio.gather(*tasks)
    
    # Generate consolidated report
    consolidated_report = consolidate_reports(reports, group_id)
    
    # Save consolidated report
    reports_dir = os.getenv("REPORTS_DIR", "reports")
    generator = ReportGenerator(output_dir=reports_dir)
    md_path, json_path = generator.save_consolidated_report(consolidated_report, group_id)
    
    return {
        "group_id": group_id,
        "session_ids": session_ids,
        "reports": reports,
        "consolidated_report_paths": {
            "markdown": md_path,
            "json": json_path
        }
    }


def consolidate_reports(reports: List[AdversarialReport], group_id: str) -> Dict[str, Any]:
    """Consolidate multiple adversarial reports into a single report"""
    from adversarial_agent import VulnerabilityType
    
    all_vulnerabilities = []
    all_conversation_history = []
    total_turns = 0
    risk_summary = {}
    
    # Initialize risk summary
    for vuln_type in VulnerabilityType:
        risk_summary[vuln_type.value] = 0
    
    # Aggregate data from all reports
    start_times = []
    end_times = []
    all_network_stats = []
    
    for report in reports:
        all_vulnerabilities.extend(report.vulnerabilities_found)
        all_conversation_history.extend(report.conversation_history)
        total_turns += report.total_turns
        start_times.append(report.start_time)
        end_times.append(report.end_time)
        if report.network_stats:
            all_network_stats.append(report.network_stats)
        
        # Aggregate risk summary
        for vuln_type, count in report.risk_summary.items():
            risk_summary[vuln_type] = risk_summary.get(vuln_type, 0) + count
    
    # Calculate overall timing
    overall_start = min(start_times) if start_times else datetime.now()
    overall_end = max(end_times) if end_times else datetime.now()
    overall_duration = (overall_end - overall_start).total_seconds() / 60
    
    # Aggregate network stats
    aggregated_network_stats = {}
    if all_network_stats:
        response_times = []
        query_times = []
        analysis_times = []
        total_requests = 0
        
        for stats in all_network_stats:
            if stats.get("avg_response_time_ms"):
                response_times.append(stats["avg_response_time_ms"])
            if stats.get("avg_query_generation_time_ms"):
                query_times.append(stats["avg_query_generation_time_ms"])
            if stats.get("avg_analysis_time_ms"):
                analysis_times.append(stats["avg_analysis_time_ms"])
            total_requests += stats.get("total_requests", 0)
        
        if response_times:
            aggregated_network_stats = {
                "avg_response_time_ms": sum(response_times) / len(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "total_requests": total_requests,
                "avg_query_generation_time_ms": sum(query_times) / len(query_times) if query_times else 0,
                "avg_analysis_time_ms": sum(analysis_times) / len(analysis_times) if analysis_times else 0,
            }
    
    # Generate consolidated recommendations
    recommendations = []
    if risk_summary.get(VulnerabilityType.HALLUCINATION.value, 0) > 0:
        recommendations.append("Implement stricter context grounding checks to prevent hallucinations")
    if risk_summary.get(VulnerabilityType.INFORMATION_LEAKAGE.value, 0) > 0:
        recommendations.append("Review and sanitize knowledge base content for sensitive information")
    if risk_summary.get(VulnerabilityType.POLICY_VIOLATION.value, 0) > 0:
        recommendations.append("Strengthen safety filters and policy enforcement mechanisms")
    if risk_summary.get(VulnerabilityType.INCONSISTENCY.value, 0) > 0:
        recommendations.append("Add consistency checks across conversation turns")
    if risk_summary.get(VulnerabilityType.CONTEXT_DRIFT.value, 0) > 0:
        recommendations.append("Improve context adherence and KB grounding")
    if risk_summary.get(VulnerabilityType.JAILEBREAK.value, 0) > 0:
        recommendations.append("Implement stronger instruction following and jailbreak detection")
    
    if not recommendations:
        recommendations.append("No critical vulnerabilities detected. Continue monitoring and testing.")
    
    # Get session IDs from reports
    session_ids = [report.session_id for report in reports]
    
    return {
        "group_id": group_id,
        "session_ids": session_ids,
        "start_time": overall_start,
        "end_time": overall_end,
        "duration_minutes": overall_duration,
        "total_turns": total_turns,
        "total_agents": len(reports),
        "vulnerabilities_found": all_vulnerabilities,
        "risk_summary": risk_summary,
        "conversation_history": all_conversation_history,
        "recommendations": recommendations,
        "network_stats": aggregated_network_stats,
        "individual_reports": [
            {
                "session_id": report.session_id,
                "total_turns": report.total_turns,
                "vulnerabilities_count": len(report.vulnerabilities_found),
                "duration_minutes": report.duration_minutes
            }
            for report in reports
        ]
    }

