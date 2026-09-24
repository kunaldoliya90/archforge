# Getting started

Run ArchForge on your machine and see a change go live.

## Prerequisites

| Tool | Why |
|---|---|
| **Python 3.10+** | Starts the dev loop |
| **Docker Desktop** | Supplies Graphviz and all Python packages, so you don't install anything else |

You don't need Graphviz, `make` or `pip install` on your machine. If they're missing, the watcher runs everything inside Docker.

## Run it

1. Start **Docker Desktop** and wait until it reports that it's running.
2. Open a terminal in the repository folder and run:

    ```bash
    python watch.py --serve
    ```

    On macOS or Linux, use `python3` if `python` isn't found.

3. Wait for the ready message. The first run builds the Docker image, which takes 1–2 minutes. Later runs start in seconds.

    ```text
    ✔ architecture/example_event_pipeline.py (0.48s)
    ✔ architecture/example_web_app.py (0.32s)
    🌐 Serving http://localhost:8000
    👀 Watching architecture/*.py, docs/, theme/ (polling). Ctrl+C to stop.
    ```

4. Open <http://localhost:8000>.

## Make your first change

1. Open `architecture/example_web_app.py`.
2. Change a label, for example `Users("Users")` to `Users("Customers")`.
3. Save. Within about two seconds the diagram in your browser updates on its own.

If the file has an error, the terminal prints a red `✘` with the Python traceback and keeps running. Fix the file and save again.

## Stop it

Press <kbd>Ctrl</kbd> <kbd>C</kbd> in the terminal.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop isn't running. Start it and try again. |
| `port is already allocated` | Something else is using port 8000. Run `docker compose down` or stop the other program. |
| `python: command not found` | Use `python3`, or install Python from python.org. |
| Browser shows the old diagram | Look for a red `✘` in the terminal. The diagram file has an error. |

<details markdown="1">
<summary>Running without Docker (faster renders)</summary>

If Graphviz is installed (`dot -V` prints a version), you can run natively:

```bash
pip install -r requirements.txt
python watch.py --serve --local
```

Install Graphviz with `winget install Graphviz.Graphviz` (Windows), `brew install graphviz` (macOS) or `sudo apt install graphviz` (Debian/Ubuntu).
</details>
