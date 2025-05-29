import time
import sys
import threading
import click
import docker

from .. import echo
from . import ersilia_cli


from ersilia.cli.commands.fetch import fetch_cmd
from ersilia.cli.commands.serve import serve_cmd
from ersilia.cli.commands.run import run_cmd


fetch_fn = fetch_cmd().callback
serve_fn = serve_cmd().callback
run_fn = run_cmd().callback

def performance_cmd():
    """
    Registers the `performance` CLI command for benchmarking model performance.
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
    fetch_fn(
        model=model_id,
        overwrite=True,
        from_dir=None,
        from_github=False,
        from_dockerhub=False,
        version=None,
        from_s3=False,
        from_hosted=False,
        hosted_url=None,
        with_bentoml=False,
        with_fastapi=False,
        quiet=None,
    )

    _log_step("Serving model", model_id)
    serve_fn(
        model=model_id,
        port=None,
        track=False,
        tracking_use_case="local",
        enable_local_cache=True,
        local_cache_only=False,
        cloud_cache_only=False,
        cache_only=False,
        max_memory=None,
        quiet=None,
    )

    _log_step("Generating example input")
   

    container = _get_model_container(model_id)
    if not container:
        raise RuntimeError("Could not find running container for the model")

    _log_step("Running model and monitoring performance")
    cpu_usages, mem_usages, duration = _monitor_and_run(container, model_id, input_file, output_file)

    _log_step("Closing model")
   

    _report_performance(model_id, cpu_usages, mem_usages, duration)

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
            run_fn(
                input=input_file,
                output=output_file,
                batch_size=100,
                as_table=False,
                quiet=None,
            )
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

