#!/usr/bin/env python3
"""
Summit Cluster Status Monitor

A comprehensive script to check the status of all pods, deployments, and services
in the Summit Kubernetes cluster. Provides clear, organized output that's easy to
understand without requiring deep Kubernetes or GCP knowledge.

Usage:
    python scripts/cluster_status.py
    python scripts/cluster_status.py --namespace summit
    python scripts/cluster_status.py --detailed
    python scripts/cluster_status.py --watch
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")


def print_section(text: str) -> None:
    """Print a formatted section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'-' * len(text)}{Colors.END}")


def print_success(text: str) -> None:
    """Print success message"""
    print(f"{Colors.GREEN} {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print warning message"""
    print(f"{Colors.YELLOW} {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print error message"""
    print(f"{Colors.RED} {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def run_kubectl(args: List[str]) -> Tuple[int, str, str]:
    """Run kubectl command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            ["kubectl"] + args, capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", "kubectl not found in PATH"
    except Exception as e:
        return 1, "", f"Error running kubectl: {e}"


def check_kubectl_access() -> bool:
    """Check if kubectl is available and can access cluster"""
    print_section("Cluster Connection")

    # Check if kubectl is installed
    code, stdout, stderr = run_kubectl(["version", "--client"])
    if code != 0:
        print_error(f"kubectl is not available: {stderr}")
        return False

    print_success("kubectl is available")

    # Check cluster connection
    code, stdout, stderr = run_kubectl(["cluster-info"])
    if code != 0:
        print_error(f"Cannot connect to cluster: {stderr}")
        print_info(
            "Run: gcloud container clusters get-credentials summit-cluster --region us-central1"
        )
        return False

    # Extract cluster info
    lines = stdout.strip().split("\n")
    for line in lines:
        if "Kubernetes control plane" in line or "Kubernetes master" in line:
            print_success(f"Connected to cluster")
            print(f"  {line}")
            break

    return True


def get_cluster_info() -> Dict[str, Any]:
    """Get basic cluster information"""
    info = {}

    # Get current context
    code, stdout, _ = run_kubectl(["config", "current-context"])
    if code == 0:
        info["context"] = stdout.strip()

    # Get cluster version
    code, stdout, _ = run_kubectl(["version", "--short"])
    if code == 0:
        for line in stdout.split("\n"):
            if "Server Version" in line:
                info["version"] = (
                    line.split(": ")[1] if ": " in line else "unknown"
                )
                break

    return info


def format_age(timestamp: str) -> str:
    """Format timestamp to human readable age"""
    try:
        # Parse Kubernetes timestamp
        if "T" in timestamp and "Z" in timestamp:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            return timestamp

        now = datetime.now(dt.tzinfo)
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days}d"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m"
        else:
            return f"{diff.seconds}s"
    except Exception:
        return timestamp


def format_resources(resources: Dict[str, str]) -> str:
    """Format resource requests/limits"""
    if not resources:
        return "none"

    parts = []
    if "cpu" in resources:
        parts.append(f"CPU: {resources['cpu']}")
    if "memory" in resources:
        parts.append(f"Mem: {resources['memory']}")

    return ", ".join(parts) if parts else "none"


def check_namespaces(target_namespace: Optional[str] = None) -> List[str]:
    """Get list of namespaces to check"""
    print_section("Namespaces")

    if target_namespace:
        # Check if specific namespace exists
        code, _, _ = run_kubectl(["get", "namespace", target_namespace])
        if code == 0:
            print_success(f"Using namespace: {target_namespace}")
            return [target_namespace]
        else:
            print_error(f"Namespace '{target_namespace}' not found")
            return []

    # Get all namespaces
    code, stdout, stderr = run_kubectl(["get", "namespaces", "-o", "json"])
    if code != 0:
        print_error(f"Failed to get namespaces: {stderr}")
        return []

    try:
        data = json.loads(stdout)
        namespaces = []

        for ns in data.get("items", []):
            name = ns.get("metadata", {}).get("name", "")
            status = ns.get("status", {}).get("phase", "")

            # Focus on relevant namespaces
            if (
                name in ["summit", "default", "kube-system"]
                or "summit" in name
            ):
                namespaces.append(name)

                if status == "Active":
                    print_success(f"{name}")
                else:
                    print_warning(f"{name} ({status})")

        return namespaces

    except json.JSONDecodeError:
        print_error("Failed to parse namespace data")
        return []


def check_deployments(namespace: str, detailed: bool = False) -> None:
    """Check deployment status in namespace"""
    print_section(f"Deployments in {namespace}")

    code, stdout, stderr = run_kubectl(
        ["get", "deployments", "-n", namespace, "-o", "json"]
    )

    if code != 0:
        print_error(f"Failed to get deployments: {stderr}")
        return

    try:
        data = json.loads(stdout)
        deployments = data.get("items", [])

        if not deployments:
            print_info("No deployments found")
            return

        for deployment in deployments:
            metadata = deployment.get("metadata", {})
            spec = deployment.get("spec", {})
            status = deployment.get("status", {})

            name = metadata.get("name", "unknown")
            labels = metadata.get("labels", {})
            created = metadata.get("creationTimestamp", "")

            desired = spec.get("replicas", 0)
            ready = status.get("readyReplicas", 0)
            available = status.get("availableReplicas", 0)
            updated = status.get("updatedReplicas", 0)

            # Determine status
            if ready == desired and available == desired:
                print_success(f"{name}")
                status_text = f"Ready: {ready}/{desired}"
            elif ready < desired:
                print_warning(f"{name}")
                status_text = f"Not Ready: {ready}/{desired}"
            else:
                print_info(f"{name}")
                status_text = f"Ready: {ready}/{desired}"

            print(f"  {status_text}")
            print(f"  Age: {format_age(created)}")

            if "version" in labels:
                print(f"  Version: {labels['version']}")

            # Show conditions if detailed
            if detailed:
                conditions = status.get("conditions", [])
                for condition in conditions:
                    ctype = condition.get("type", "")
                    cstatus = condition.get("status", "")
                    reason = condition.get("reason", "")

                    if ctype == "Available":
                        if cstatus == "True":
                            print(f"   Available")
                        else:
                            print(f"   Not Available: {reason}")
                    elif ctype == "Progressing":
                        if cstatus == "True":
                            print(f"   Progressing")
                        else:
                            print(f"   Not Progressing: {reason}")

            print()

    except json.JSONDecodeError:
        print_error("Failed to parse deployment data")


def check_pods(namespace: str, detailed: bool = False) -> None:
    """Check pod status in namespace"""
    print_section(f"Pods in {namespace}")

    code, stdout, stderr = run_kubectl(
        ["get", "pods", "-n", namespace, "-o", "json"]
    )

    if code != 0:
        print_error(f"Failed to get pods: {stderr}")
        return

    try:
        data = json.loads(stdout)
        pods = data.get("items", [])

        if not pods:
            print_info("No pods found")
            return

        # Group pods by deployment/app
        pod_groups = {}
        for pod in pods:
            metadata = pod.get("metadata", {})
            labels = metadata.get("labels", {})

            app = labels.get("app", labels.get("k8s-app", "unknown"))
            if app not in pod_groups:
                pod_groups[app] = []
            pod_groups[app].append(pod)

        for app, app_pods in pod_groups.items():
            print(f"\n{Colors.BOLD}{app}:{Colors.END}")

            for pod in app_pods:
                metadata = pod.get("metadata", {})
                spec = pod.get("spec", {})
                status = pod.get("status", {})

                name = metadata.get("name", "unknown")
                created = metadata.get("creationTimestamp", "")

                phase = status.get("phase", "Unknown")
                ready_conditions = [
                    c
                    for c in status.get("conditions", [])
                    if c.get("type") == "Ready"
                ]

                is_ready = (
                    ready_conditions
                    and ready_conditions[0].get("status") == "True"
                )

                # Determine status color and symbol
                if phase == "Running" and is_ready:
                    print_success(f"  {name}")
                elif phase == "Running" and not is_ready:
                    print_warning(f"  {name}")
                elif phase in ["Pending", "ContainerCreating"]:
                    print_info(f"  {name}")
                else:
                    print_error(f"  {name}")

                print(f"    Status: {phase}")
                print(f"    Age: {format_age(created)}")

                # Show container status
                container_statuses = status.get("containerStatuses", [])
                for container_status in container_statuses:
                    container_name = container_status.get("name", "")
                    ready = container_status.get("ready", False)
                    restart_count = container_status.get("restartCount", 0)

                    state = container_status.get("state", {})
                    if "running" in state:
                        started = state["running"].get("startedAt", "")
                        print(
                            f"    Container {container_name}: Running (restarts: {restart_count})"
                        )
                        if started:
                            print(f"      Started: {format_age(started)} ago")
                    elif "waiting" in state:
                        reason = state["waiting"].get("reason", "Unknown")
                        print(
                            f"    Container {container_name}: Waiting ({reason})"
                        )
                    elif "terminated" in state:
                        reason = state["terminated"].get("reason", "Unknown")
                        exit_code = state["terminated"].get("exitCode", "")
                        print(
                            f"    Container {container_name}: Terminated ({reason}, exit: {exit_code})"
                        )

                # Show resource usage if detailed
                if detailed:
                    containers = spec.get("containers", [])
                    for container in containers:
                        container_name = container.get("name", "")
                        resources = container.get("resources", {})

                        requests = format_resources(
                            resources.get("requests", {})
                        )
                        limits = format_resources(resources.get("limits", {}))

                        if requests != "none" or limits != "none":
                            print(f"    Resources ({container_name}):")
                            if requests != "none":
                                print(f"      Requests: {requests}")
                            if limits != "none":
                                print(f"      Limits: {limits}")

                print()

    except json.JSONDecodeError:
        print_error("Failed to parse pod data")


def check_services(namespace: str) -> None:
    """Check service status in namespace"""
    print_section(f"Services in {namespace}")

    code, stdout, stderr = run_kubectl(
        ["get", "services", "-n", namespace, "-o", "json"]
    )

    if code != 0:
        print_error(f"Failed to get services: {stderr}")
        return

    try:
        data = json.loads(stdout)
        services = data.get("items", [])

        if not services:
            print_info("No services found")
            return

        for service in services:
            metadata = service.get("metadata", {})
            spec = service.get("spec", {})

            name = metadata.get("name", "unknown")
            service_type = spec.get("type", "ClusterIP")
            cluster_ip = spec.get("clusterIP", "")
            ports = spec.get("ports", [])

            print_success(f"{name}")
            print(f"  Type: {service_type}")
            print(f"  Cluster IP: {cluster_ip}")

            if ports:
                port_info = []
                for port in ports:
                    port_name = port.get("name", "")
                    port_num = port.get("port", "")
                    target_port = port.get("targetPort", "")
                    protocol = port.get("protocol", "TCP")

                    if port_name:
                        port_info.append(
                            f"{port_name}:{port_num}->{target_port}/{protocol}"
                        )
                    else:
                        port_info.append(
                            f"{port_num}->{target_port}/{protocol}"
                        )

                print(f"  Ports: {', '.join(port_info)}")

            # Show external endpoints for LoadBalancer/NodePort
            if service_type == "LoadBalancer":
                status = service.get("status", {})
                ingress = status.get("loadBalancer", {}).get("ingress", [])
                if ingress:
                    for ing in ingress:
                        ip = ing.get("ip", ing.get("hostname", ""))
                        if ip:
                            print(f"  External IP: {ip}")

            print()

    except json.JSONDecodeError:
        print_error("Failed to parse service data")


def check_events(namespace: str, limit: int = 10) -> None:
    """Check recent events in namespace"""
    print_section(f"Recent Events in {namespace}")

    code, stdout, stderr = run_kubectl(
        [
            "get",
            "events",
            "-n",
            namespace,
            "--sort-by=.lastTimestamp",
            "-o",
            "json",
        ]
    )

    if code != 0:
        print_error(f"Failed to get events: {stderr}")
        return

    try:
        data = json.loads(stdout)
        events = data.get("items", [])

        if not events:
            print_info("No recent events")
            return

        # Show last N events
        recent_events = events[-limit:] if len(events) > limit else events

        for event in reversed(recent_events):  # Show newest first
            metadata = event.get("metadata", {})

            event_type = event.get("type", "Normal")
            reason = event.get("reason", "")
            message = event.get("message", "")
            timestamp = event.get("lastTimestamp", "")
            involved_object = event.get("involvedObject", {})

            obj_kind = involved_object.get("kind", "")
            obj_name = involved_object.get("name", "")

            age = format_age(timestamp) if timestamp else ""

            # Color code by event type
            if event_type == "Warning":
                print_warning(f"{age} {obj_kind}/{obj_name}: {reason}")
            else:
                print_info(f"{age} {obj_kind}/{obj_name}: {reason}")

            if message and message != reason:
                print(f"  {message}")

            print()

    except json.JSONDecodeError:
        print_error("Failed to parse events data")


def get_cluster_summary(namespaces: List[str]) -> Dict[str, Any]:
    """Get overall cluster summary"""
    summary = {
        "total_namespaces": len(namespaces),
        "total_deployments": 0,
        "healthy_deployments": 0,
        "total_pods": 0,
        "running_pods": 0,
        "total_services": 0,
    }

    for namespace in namespaces:
        # Count deployments
        code, stdout, _ = run_kubectl(
            ["get", "deployments", "-n", namespace, "-o", "json"]
        )
        if code == 0:
            try:
                data = json.loads(stdout)
                deployments = data.get("items", [])
                summary["total_deployments"] += len(deployments)

                for deployment in deployments:
                    status = deployment.get("status", {})
                    desired = deployment.get("spec", {}).get("replicas", 0)
                    ready = status.get("readyReplicas", 0)

                    if ready == desired and desired > 0:
                        summary["healthy_deployments"] += 1
            except json.JSONDecodeError:
                pass

        # Count pods
        code, stdout, _ = run_kubectl(
            ["get", "pods", "-n", namespace, "-o", "json"]
        )
        if code == 0:
            try:
                data = json.loads(stdout)
                pods = data.get("items", [])
                summary["total_pods"] += len(pods)

                for pod in pods:
                    phase = pod.get("status", {}).get("phase", "")
                    if phase == "Running":
                        summary["running_pods"] += 1
            except json.JSONDecodeError:
                pass

        # Count services
        code, stdout, _ = run_kubectl(
            ["get", "services", "-n", namespace, "-o", "json"]
        )
        if code == 0:
            try:
                data = json.loads(stdout)
                services = data.get("items", [])
                summary["total_services"] += len(services)
            except json.JSONDecodeError:
                pass

    return summary


def print_cluster_summary(summary: Dict[str, Any]) -> None:
    """Print cluster summary"""
    print_section("Cluster Summary")

    print(f"Namespaces: {summary['total_namespaces']}")
    print(
        f"Deployments: {summary['healthy_deployments']}/{summary['total_deployments']} healthy"
    )
    print(f"Pods: {summary['running_pods']}/{summary['total_pods']} running")
    print(f"Services: {summary['total_services']}")

    # Overall health indicator
    deployment_health = (
        summary["healthy_deployments"] / summary["total_deployments"]
        if summary["total_deployments"] > 0
        else 1.0
    )
    pod_health = (
        summary["running_pods"] / summary["total_pods"]
        if summary["total_pods"] > 0
        else 1.0
    )

    overall_health = (deployment_health + pod_health) / 2

    if overall_health >= 0.9:
        print_success("Overall Status: Healthy")
    elif overall_health >= 0.7:
        print_warning("Overall Status: Degraded")
    else:
        print_error("Overall Status: Unhealthy")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Summit Cluster Status Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Check all relevant namespaces
  %(prog)s -n summit                # Check only summit namespace
  %(prog)s --detailed               # Show detailed information
  %(prog)s --watch                  # Continuous monitoring
  %(prog)s --events-only            # Show only recent events
        """,
    )

    parser.add_argument(
        "-n",
        "--namespace",
        help="Specific namespace to check (default: check summit, default, kube-system)",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information including resource usage and conditions",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuous monitoring (refresh every 30 seconds)",
    )
    parser.add_argument(
        "--events-only", action="store_true", help="Show only recent events"
    )
    parser.add_argument(
        "--no-events", action="store_true", help="Skip events section"
    )

    args = parser.parse_args()

    def run_check():
        """Run the status check"""
        print_header("Summit Cluster Status")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Check kubectl access
        if not check_kubectl_access():
            return False

        # Show cluster info
        cluster_info = get_cluster_info()
        if cluster_info:
            print_info(f"Context: {cluster_info.get('context', 'unknown')}")
            if "version" in cluster_info:
                print_info(f"Version: {cluster_info['version']}")

        # Get namespaces to check
        namespaces = check_namespaces(args.namespace)
        if not namespaces:
            return False

        # If only showing events, do that and exit
        if args.events_only:
            for namespace in namespaces:
                check_events(namespace, limit=20)
            return True

        # Check each namespace
        for namespace in namespaces:
            check_deployments(namespace, args.detailed)
            check_pods(namespace, args.detailed)
            check_services(namespace)

            if not args.no_events:
                check_events(namespace, limit=5)

        # Show summary
        summary = get_cluster_summary(namespaces)
        print_cluster_summary(summary)

        return True

    try:
        if args.watch:
            print("Starting continuous monitoring (Ctrl+C to stop)...")
            while True:
                # Clear screen
                print("\033[2J\033[H")

                success = run_check()
                if not success:
                    break

                print(
                    f"\n{Colors.BLUE}Refreshing in 30 seconds...{Colors.END}"
                )
                time.sleep(30)
        else:
            success = run_check()
            sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped by user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
