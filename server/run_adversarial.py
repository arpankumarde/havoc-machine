#!/usr/bin/env python3

"""
Adversarial Testing System for Havoc Machine

This script runs adversarial tests against the RAG AI system to find
vulnerabilities, loopholes, and drifts in the system.
"""

import os
import asyncio
import argparse
from dotenv import load_dotenv
from adversarial_agent import AdversarialAgent
from report_generator import ReportGenerator

load_dotenv()

# Configuration from environment
ADVERSARIAL_MODEL = os.getenv("ADVERSARIAL_MODEL", "openai/gpt-4o")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-4o")
AGENT_HOST = os.getenv("AGENT_HOST", "localhost")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
DEFAULT_DURATION_MINUTES = float(os.getenv("ADVERSARIAL_DURATION_MINUTES", "5"))
REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")


async def main():
    parser = argparse.ArgumentParser(
        description="Run adversarial tests against the Havoc Machine RAG AI system"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION_MINUTES,
        help=f"Duration of the test in minutes (default: {DEFAULT_DURATION_MINUTES})"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=ADVERSARIAL_MODEL,
        help=f"Adversarial model to use (default: {ADVERSARIAL_MODEL})"
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=JUDGE_MODEL,
        help=f"Judge model to use for analysis (default: {JUDGE_MODEL})"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=AGENT_HOST,
        help=f"Agent server host (default: {AGENT_HOST})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=AGENT_PORT,
        help=f"Agent server port (default: {AGENT_PORT})"
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Custom session ID (default: auto-generated)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=REPORTS_DIR,
        help=f"Output directory for reports (default: {REPORTS_DIR})"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("HAVOC MACHINE - Adversarial Testing System")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Duration: {args.duration} minutes")
    print(f"  Adversarial Model: {args.model} (for query generation)")
    print(f"  Judge Model: {args.judge_model} (for analysis & reporting)")
    print(f"  Target: ws://{args.host}:{args.port}/ws/{{session_id}}")
    print(f"  Reports Directory: {args.output_dir}")
    print("="*60 + "\n")
    
    # Create adversarial agent
    agent = AdversarialAgent(
        adversarial_model=args.model,
        judge_model=args.judge_model,
        agent_host=args.host,
        agent_port=args.port,
        session_id=args.session_id
    )
    
    # Run adversarial test
    try:
        report = await agent.run_adversarial_test(duration_minutes=args.duration)
        
        # Generate and save reports
        print("\n" + "="*60)
        print("Generating Reports...")
        print("="*60)
        
        generator = ReportGenerator(output_dir=args.output_dir)
        md_path, json_path = generator.save_both_formats(report)
        
        print(f"\n✅ Reports saved:")
        print(f"  Markdown: {md_path}")
        print(f"  JSON: {json_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Total Turns: {report.total_turns}")
        print(f"Vulnerabilities Found: {len(report.vulnerabilities_found)}")
        print(f"Duration: {report.duration_minutes:.2f} minutes")
        print("\nVulnerability Breakdown:")
        for vuln_type, count in report.risk_summary.items():
            if count > 0:
                print(f"  - {vuln_type.replace('_', ' ').title()}: {count}")
        
        if report.recommendations:
            print("\nTop Recommendations:")
            for i, rec in enumerate(report.recommendations[:3], 1):
                print(f"  {i}. {rec}")
        
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during adversarial test: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

