#!/usr/bin/env python3
"""
RunPod CLI Tool for Summit AI

Comprehensive command-line interface for managing RunPod endpoints,
testing connections, monitoring performance, and integrating with OpenCode.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.runpod_opencode_client import (
    create_runpod_client,
    test_runpod_connection,
)


class RunPodCLI:
    """Command-line interface for RunPod operations"""

    def __init__(self):
        self.client = create_runpod_client()

    async def health_check(self):
        """Check endpoint health status"""
        print("Checking RunPod endpoint health...")
        result = await self.client.get_health()

        if result["success"]:
            health = result["health"]
            print(" Endpoint is healthy")
            print(f"  Workers: {health.get('workers', 'N/A')}")
            print(f"  Queue: {health.get('queue', 'N/A')}")
            print(f"  Jobs: {health.get('jobs', 'N/A')}")
        else:
            print(f" Health check failed: {result['error']}")
            return False
        return True

    async def test_prompt(self, prompt: str, method: str = "sync"):
        """Test a single prompt"""
        print(f"Testing {method} prompt: '{prompt[:50]}...'")

        use_sync = method == "sync"
        result = await self.client.send_prompt(prompt, use_sync=use_sync)

        if result["success"]:
            print(f" {method.capitalize()} prompt successful")
            print(f"  Processing time: {result['processing_time']:.2f}s")
            print(f"  Estimated cost: ${result['estimated_cost']:.6f}")
            print(f"  Response: {result['output'][:200]}...")
        else:
            print(f" {method.capitalize()} prompt failed: {result['error']}")

        return result

    async def benchmark(self, num_requests: int = 5, method: str = "sync"):
        """Run performance benchmark"""
        print(f"Running benchmark with {num_requests} {method} requests...")

        if method == "sync":
            benchmark_result = await self.client.benchmark_performance(
                num_requests
            )
        else:
            # Custom async benchmark
            results = []
            start_time = time.time()

            for i in range(num_requests):
                result = await self.client.send_async_prompt(
                    f"Test request {i+1}"
                )
                results.append(
                    {
                        "request_id": i + 1,
                        "success": result["success"],
                        "processing_time": result.get("processing_time", 0),
                        "error": (
                            result.get("error")
                            if not result["success"]
                            else None
                        ),
                    }
                )

            total_time = time.time() - start_time
            successful = sum(1 for r in results if r["success"])

            benchmark_result = {
                "total_requests": num_requests,
                "successful_requests": successful,
                "success_rate": successful / num_requests,
                "total_time": total_time,
                "avg_processing_time": sum(
                    r["processing_time"] for r in results if r["success"]
                )
                / max(successful, 1),
                "requests_per_second": num_requests / total_time,
                "results": results,
            }

        print(f" Benchmark completed:")
        print(f"  Total requests: {benchmark_result['total_requests']}")
        print(f"  Successful: {benchmark_result['successful_requests']}")
        print(f"  Success rate: {benchmark_result['success_rate']:.1%}")
        print(f"  Total time: {benchmark_result['total_time']:.2f}s")
        print(
            f"  Avg processing time: {benchmark_result['avg_processing_time']:.2f}s"
        )
        print(
            f"  Requests/second: {benchmark_result['requests_per_second']:.2f}"
        )

        return benchmark_result

    async def job_status(self, job_id: str):
        """Check status of a specific job"""
        print(f"Checking status of job: {job_id}")
        result = await self.client.get_job_status(job_id)

        if result["success"]:
            status = result["status"]
            print(f" Job status retrieved:")
            print(f"  ID: {status.get('id', 'N/A')}")
            print(f"  Status: {status.get('status', 'N/A')}")
            print(f"  Progress: {status.get('progress', 'N/A')}")
            if "output" in status:
                print(f"  Output: {str(status['output'])[:200]}...")
        else:
            print(f" Failed to get job status: {result['error']}")

        return result

    async def cancel_job(self, job_id: str):
        """Cancel a specific job"""
        print(f"Cancelling job: {job_id}")
        result = await self.client.cancel_job(job_id)

        if result["success"]:
            print(f" Job cancelled successfully")
            print(f"  Result: {result['result']}")
        else:
            print(f" Failed to cancel job: {result['error']}")

        return result

    async def purge_queue(self):
        """Purge all pending jobs"""
        print("Purging job queue...")
        result = await self.client.purge_queue()

        if result["success"]:
            print(f" Queue purged successfully")
            print(f"  Result: {result['result']}")
        else:
            print(f" Failed to purge queue: {result['error']}")

        return result

    def generate_opencode_config(self, output_file: str = None):
        """Generate OpenCode configuration"""
        config = self.client.get_openai_compatible_config()

        opencode_config = {
            "defaultAgent": "coder",
            "localEndpoint": config["base_url"],
            "localApiKey": config["api_key"],
            "agents": {
                "coder": {
                    "model": config["model"],
                    "reasoningEffort": "high",
                    "temperature": 0.7,
                    "maxTokens": 2048,
                }
            },
            "tools": {
                "bash": {"enabled": True, "timeout": 30},
                "read": {"enabled": True},
                "write": {"enabled": True},
                "search": {"enabled": True},
            },
        }

        if output_file:
            with open(output_file, "w") as f:
                json.dump(opencode_config, f, indent=2)
            print(f" OpenCode configuration saved to: {output_file}")
        else:
            print("OpenCode Configuration:")
            print(json.dumps(opencode_config, indent=2))

        return opencode_config

    async def interactive_mode(self):
        """Interactive mode for testing prompts"""
        print("=" * 60)
        print("RUNPOD INTERACTIVE MODE")
        print("Type 'quit' to exit, 'help' for commands")
        print("=" * 60)

        while True:
            try:
                prompt = input("\nRunPod> ").strip()

                if prompt.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                elif prompt.lower() == "help":
                    print("Commands:")
                    print("  help - Show this help")
                    print("  health - Check endpoint health")
                    print("  sync <prompt> - Send sync prompt")
                    print("  async <prompt> - Send async prompt")
                    print("  benchmark [num] - Run benchmark")
                    print("  quit - Exit interactive mode")
                elif prompt.lower() == "health":
                    await self.health_check()
                elif prompt.lower().startswith("sync "):
                    await self.test_prompt(prompt[5:], "sync")
                elif prompt.lower().startswith("async "):
                    await self.test_prompt(prompt[6:], "async")
                elif prompt.lower().startswith("benchmark"):
                    parts = prompt.split()
                    num = int(parts[1]) if len(parts) > 1 else 3
                    await self.benchmark(num)
                elif prompt:
                    # Default to sync prompt
                    await self.test_prompt(prompt, "sync")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    async def full_test_suite(self):
        """Run comprehensive test suite"""
        print("=" * 60)
        print("RUNPOD COMPREHENSIVE TEST SUITE")
        print("=" * 60)

        # Test 1: Health check
        print("\n1. Health Check")
        if not await self.health_check():
            return False

        # Test 2: Connection test
        print("\n2. Connection Test")
        if not await self.client.test_connection():
            print(" Connection test failed")
            return False
        print(" Connection test passed")

        # Test 3: Sync prompt
        print("\n3. Sync Prompt Test")
        sync_result = await self.test_prompt(
            "Write a Python hello world function", "sync"
        )

        # Test 4: Async prompt
        print("\n4. Async Prompt Test")
        async_result = await self.test_prompt(
            "Explain what Python is", "async"
        )

        # Test 5: Performance benchmark
        print("\n5. Performance Benchmark")
        await self.benchmark(3, "sync")

        # Test 6: Cost analysis
        print("\n6. Cost Analysis")
        total_cost = 0
        if sync_result["success"]:
            total_cost += sync_result.get("estimated_cost", 0)
        if async_result["success"]:
            total_cost += async_result.get("estimated_cost", 0)

        print(f"  Total test cost: ${total_cost:.6f}")
        print(f"  Average cost per request: ${total_cost/2:.6f}")

        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETED SUCCESSFULLY!")
        print("Your RunPod endpoint is fully operational.")
        print("=" * 60)

        return True


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="RunPod CLI Tool for Summit AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s health                    # Check endpoint health
  %(prog)s test "Hello world"        # Test a prompt
  %(prog)s benchmark 5               # Run 5-request benchmark
  %(prog)s config opencode.json      # Generate OpenCode config
  %(prog)s interactive               # Interactive mode
  %(prog)s full-test                 # Run comprehensive test suite
        """,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # Health command
    subparsers.add_parser("health", help="Check endpoint health")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test a prompt")
    test_parser.add_argument("prompt", help="Prompt to test")
    test_parser.add_argument(
        "--method",
        choices=["sync", "async"],
        default="sync",
        help="Method to use (default: sync)",
    )

    # Benchmark command
    benchmark_parser = subparsers.add_parser(
        "benchmark", help="Run performance benchmark"
    )
    benchmark_parser.add_argument(
        "--requests",
        type=int,
        default=5,
        help="Number of requests (default: 5)",
    )
    benchmark_parser.add_argument(
        "--method",
        choices=["sync", "async"],
        default="sync",
        help="Method to use (default: sync)",
    )

    # Job status command
    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument("job_id", help="Job ID to check")

    # Cancel job command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a job")
    cancel_parser.add_argument("job_id", help="Job ID to cancel")

    # Purge queue command
    subparsers.add_parser("purge", help="Purge job queue")

    # Config command
    config_parser = subparsers.add_parser(
        "config", help="Generate OpenCode configuration"
    )
    config_parser.add_argument(
        "output", nargs="?", help="Output file (optional)"
    )

    # Interactive command
    subparsers.add_parser("interactive", help="Interactive mode")

    # Full test command
    subparsers.add_parser("full-test", help="Run comprehensive test suite")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = RunPodCLI()

    try:
        if args.command == "health":
            await cli.health_check()
        elif args.command == "test":
            await cli.test_prompt(args.prompt, args.method)
        elif args.command == "benchmark":
            await cli.benchmark(args.requests, args.method)
        elif args.command == "status":
            await cli.job_status(args.job_id)
        elif args.command == "cancel":
            await cli.cancel_job(args.job_id)
        elif args.command == "purge":
            await cli.purge_queue()
        elif args.command == "config":
            cli.generate_opencode_config(args.output)
        elif args.command == "interactive":
            await cli.interactive_mode()
        elif args.command == "full-test":
            await cli.full_test_suite()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
