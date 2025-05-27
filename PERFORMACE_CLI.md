# 📊 Ersilia Performance Command

The `ersilia performance` command allows you to **benchmark the computational performance** of any model available in the Ersilia Model Hub. It fetches, serves, and runs the model on sample input, while **measuring CPU usage, memory usage, and duration** of execution.

---

## 🔧 Command

```bash
ersilia performance <model_id>
```

---

## 🧠 What It Does

When you run this command, Ersilia will:

1. **Fetch** the specified model from DockerHub.
2. **Serve** the model in a container.
3. **Generate 100 example inputs** via `ersilia example`.
4. **Run** the model on those inputs.
5. **Monitor** CPU and memory usage while the container is running.
6. **Close** the model (stop the container).
7. **Print** a detailed performance summary.

---

## 🧪 Example

```bash
ersilia performance eos4e40
```

---

## 🖥️ Output Example

```bash
🚀 Fetching model eos4e40
🚀 Serving model eos4e40
🚀 Generating example input
🚀 Running model and monitoring performance
🚀 Closing model

📊 Performance Summary
----------------------------------------
Model:      eos4e40
CPU Avg:    48.7%
Mem Peak:   420.5 MiB
Duration:   15.32 seconds
----------------------------------------
```

---

## 📌 Requirements

- Docker must be installed and running.
- The model should support being served with `ersilia serve` and run with `ersilia run`.
- The `example` command should be available for generating inputs.

---

## ⚠️ Notes

- If the model fails to run or complete, a warning and the captured error will be displayed.
- All intermediate steps (`fetch`, `serve`, `example`, `run`, `close`) use Ersilia CLI commands and follow the standard Ersilia model lifecycle.
- Resource usage is measured every 0.5 seconds using Docker’s live container stats API.

---

## 💡 Use Case

This command is useful for:

- Benchmarking different models to compare their performance.
- Measuring resource requirements before deploying models in production.
- Debugging runtime efficiency issues.

---

## 🧼 Cleanup

The model container is automatically closed after the performance test finishes.  
Temporary input/output files (e.g., `eos4e40_input.csv`) are stored in the working directory.

---

## ✨ Maintainer Tips

If you're contributing or maintaining this command:

- The logic is implemented in `performance_cmd.py`.
- Docker is accessed using the `docker` Python SDK.
- CLI subprocesses are invoked using Python’s `subprocess.run(...)`.

---

## 🙋‍♀️ Questions?

Need help or found a bug?  
Open an issue in the [GitHub repository](https://github.com/ersilia-os/ersilia).
