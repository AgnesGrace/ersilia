import time
import sys
import threading
import click
import docker
import subprocess

from .. import echo
from . import ersilia_cli

from ersilia.hub.pull.pull import ModelPuller


def performance_cmd():
    """
    This Registers the `performance` CLI command for benchmarking model performance.
    """
    @ersilia_cli.command(
        short_help="Benchmark performance of a given model",
        help=(
            "Fetches a model, serves it, runs on 100 examples, monitors CPU/memory usage, "
            "and reports summary metrics."
        ),
    )
    @click.argument("model_id", required=True, type=click.STRING)
    def performance(model_id):
        try:
            _run_performance(model_id)
        except Exception as e:
            echo(f":x: {str(e)}", fg="red")
            sys.exit(1)

    return performance


def _run_performance(model_id):
    input_file = f"{model_id}_input.csv"
    output_file = f"{model_id}_output.csv"

    _log_step("Fetching model", model_id)
    puller = ModelPuller(model_id=model_id, overwrite=True)
    puller.pull()

    _log_step("Serving model", model_id)
    _run_cli_command("serve", model_id)

    _log_step("Generating example input")
    _run_cli_command("example", model_id, "-n", "100", "-f", input_file)

    container = _get_model_container(model_id)
    if not container:
        raise RuntimeError("Could not find running container for the model")

    _log_step("Running model and monitoring performance")
    cpu_usages, mem_usages, duration = _monitor_and_run(container, model_id, input_file, output_file)

    _log_step("Closing model")
    _run_cli_command("close")

    _report_performance(model_id, cpu_usages, mem_usages, duration)


def _run_cli_command(*args):
    cmd = ["ersilia"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"\nCommand Failed: {' '.join(cmd)}"
            f"\nExit Code: {result.returncode}"
            f"\nStdout: {result.stdout.strip()}"
            f"\nStderr: {result.stderr.strip()}"
        )
    return result.stdout


def _get_model_container(model_id):
    client = docker.from_env()
    for cont in client.containers.list():
        if model_id in cont.name or any(model_id in tag for tag in cont.image.tags):
            return cont
    return None


def _monitor_and_run(container, model_id, input_file, output_file):
    cpu_usages = []
    mem_usages = []
    run_exception = None

    def monitor():
        while run_thread.is_alive():
            try:
                stats = container.stats(stream=False)
                cpu = _calculate_cpu_percent(stats)
                mem = stats["memory_stats"]["usage"] / (1024 * 1024)
                cpu_usages.append(cpu)
                mem_usages.append(mem)
            except Exception:
                pass
            time.sleep(0.5)

    def run_model():
        nonlocal run_exception
        try:
            _run_cli_command("run", model_id, "-i", input_file, "-o", output_file)
        except Exception as e:
            run_exception = e

    start = time.time()
    run_thread = threading.Thread(target=run_model)
    monitor_thread = threading.Thread(target=monitor)
    run_thread.start()
    monitor_thread.start()
    run_thread.join()
    monitor_thread.join()
    end = time.time()

    if run_exception:
        raise run_exception

    return cpu_usages, mem_usages, end - start


def _calculate_cpu_percent(stats):
    try:
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        sys_cpu_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        cpu_count = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [])) or 1
        if sys_cpu_delta > 0:
            return (cpu_delta / sys_cpu_delta) * cpu_count * 100
    except Exception:
        pass
    return 0.0


def _log_step(step, extra=""):
    echo(f":rocket: {step} {extra}".strip(), fg="blue")


def _report_performance(model_id, cpu_usages, mem_usages, duration):
    cpu_avg = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0
    mem_peak = max(mem_usages) if mem_usages else 0

    echo("\n:bar_chart: Performance Summary")
    echo("-" * 40)
    echo(f"Model:      {model_id}")
    echo(f"CPU Avg:    {cpu_avg:.1f}%")
    echo(f"Mem Peak:   {mem_peak:.1f} MiB")
    echo(f"Duration:   {duration:.2f} seconds")
    echo("-" * 40)
