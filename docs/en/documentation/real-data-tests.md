# Real-data tests on Ubuntu

Real-data workflows can run for hours and can use a large amount of memory,
especially H3 workflows over large AOIs. Run them from a normal Ubuntu terminal
and keep any IDE as an editor only. Integrated IDE terminals are convenient
for short checks, but an IDE crash can interrupt a long process or hide the
last useful output.

## Recommended mode: tmux

Install `tmux` once if it is not already available:

```bash
sudo apt update
sudo apt install tmux procps coreutils
```

Start a named session:

```bash
tmux new -s h3-census
```

Move to the project directory and launch the real-data script:

```bash
cd /path/to/istat-census-data
poetry run python scripts/run_h3_census_analysis.py
```

For the local development layout used by the repository owner, the project
directory is usually:

```bash
cd /home/max/Desktop/DEV/PyProcess/istatcelldata_agentic/istat-census-data
```

The script already configures its own log file. If you also want to keep the full
terminal stream in a separate log, use `tee`:

```bash
poetry run python scripts/run_h3_census_analysis.py 2>&1 | tee -a /home/max/Desktop/census/logs/run_h3_census_analysis_tmux_$(date +%Y%m%dT%H%M%S).log
```

Detach without stopping the process:

```text
Ctrl-b
d
```

Reattach later:

```bash
tmux attach -t h3-census
```

List sessions:

```bash
tmux ls
```

If output appears in the terminal but not in the timestamped workflow log,
identify the pane and capture its scrollback before closing the session:

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command} #{pane_current_path} #{pane_active}'
tmux capture-pane -p -S - -t h3-census:0.0 > /home/max/Desktop/census/logs/tmux_capture_$(date +%Y%m%dT%H%M%S).log
```

Replace `h3-census:0.0` with the pane target returned by `tmux list-panes` if
the run is in a different session, window, or pane.

## Monitor the run

Find the process ID from another terminal:

```bash
pgrep -af run_h3_census_analysis.py
```

Monitor the process. `RSS` is resident memory in KB:

```bash
ps -p <PID> -o pid,ppid,stat,etime,lstart,%cpu,%mem,rss,cmd
```

Monitor system memory:

```bash
free -h
```

Monitor the intermediate directory size:

```bash
du -sh /home/max/Desktop/census/h3_intermediates
```

Follow the newest H3 workflow log:

```bash
tail -f "$(ls -t /home/max/Desktop/census/logs/run_h3_census_analysis_*.log | head -n 1)"
```

Follow a known log file:

```bash
tail -f /home/max/Desktop/census/logs/run_h3_census_analysis_YYYYMMDDTHHMMSS.log
```

## H3 real-data settings

For large AOIs, start conservatively:

- `workers = 1`
- `parallel_backend = DEFAULT_PARALLEL_BACKEND`
- `max_in_flight_chunks = None`
- `intermediate_storage = DEFAULT_INTERMEDIATE_STORAGE`
- `keep_intermediates = True`
- `retain_results = False`

Use more workers only after a conservative run proves that memory headroom is
stable. Keep `retain_results = False` for multi-year runs unless the caller
really needs all annual GeoDataFrames in memory after writing.

With the default Parquet intermediate storage, `retain_results = False` makes
the end-to-end H3 workflow stream finalized `result_chunks/` directly to the
GeoPackage. The workflow does not run a global `pd.concat` over all result chunks
before writing the layer; it still records yearly row counts and validation
tables in the workflow result.

Do not delete `h3_intermediates` until the final output has been verified. If a
run stops after writing chunk files, those intermediates are the best evidence
for triage and may allow a safer rerun when settings are unchanged.

Set `reuse_intermediates = True` only when the AOI, year, index selection,
chunking, H3 resolution, boundary ring, and intermediate directory belong to the
same intended run. If in doubt, inspect the logs first.

## Completion checks

A completed H3 workflow should write the configured output path, for example:

```text
/home/max/Desktop/census/h3_census_analysis.gpkg
```

The log should also include the final workflow summary emitted by the script:

```text
H3 census workflow completed.
H3 output: /home/max/Desktop/census/h3_census_analysis.gpkg
```

For chunked H3 runs, a log ending at a line like this means the heavy chunk phase
finished, but it does not by itself prove that the final GeoPackage was written:

```text
Completed H3 estimation chunk 1156/1156.
```

If the process is gone, the final output file is missing, and the log has no
workflow completion summary, treat the run as interrupted before final export.
Keep the intermediates and inspect the last log lines before restarting.

## Failure tracebacks and intermediate recovery

The editable `scripts/run_h3_census_analysis.py` script writes regular fatal
exceptions and user interrupts to the timestamped official log file with the
full Python traceback. The same error can still appear in `tmux` or stderr. If
the official log stops before the terminal traceback, capture the tmux pane with
`tmux capture-pane` before closing it.

If a run completes all result chunks and then fails during finalization, preserve
the intermediate directory and retry only after checking that the settings still
refer to the same AOI, year, indexes, chunk size, H3 resolution, boundary ring,
and intermediate directory.

For the editable script workflow, recovery usually means keeping:

```python
keep_intermediates = True
intermediate_dir = main_path / "h3_intermediates"
```

and changing only:

```python
reuse_intermediates = True
```

The Parquet-backed H3 finalizer can reuse retained result chunks and, for
full-cell output (`clip_output = False`), rebuild isolated unreadable H3
geometries from `h3_index` during the final merge. If clipped output is enabled
and a clipped geometry cannot be decoded or repaired, the workflow fails with a
diagnostic that names the chunk path, row number, H3 index, and geometry error.

When `result_chunks/` is complete but the process is killed before export, you
can finalize without recomputing H3 estimation:

```bash
cd /path/to/istat-census-data
poetry run python scripts/finalize_h3_result_chunks.py \
  --intermediate-workspace /path/to/h3_intermediates/<fingerprint> \
  --output-path /path/to/h3_census_analysis.gpkg
```

The script reads `metadata.json`, `prepared_source.parquet`, and
`result_chunks/result_chunk_*.parquet`, computes total validations, integerizes
additive indexes in batches, and writes the GeoPackage layer by appending one
chunk at a time. The default output layer is
`h3_census<year>_r<h3_resolution>`; if the layer already exists, the script
fails before writing to avoid duplicate features.

Each yearly H3 layer treats `h3_index` as a design key. During export, the script
rejects chunks with null or duplicate `h3_index` values, creates a GeoPackage
`UNIQUE INDEX` on `h3_index`, and verifies that the layer's RTree spatial index
exists. Different census years should be written to separate layers, not into the
same table.

## Alternatives

Use `screen` if `tmux` is unavailable:

```bash
screen -S h3-census
cd /path/to/istat-census-data
poetry run python scripts/run_h3_census_analysis.py
```

Detach from `screen` with `Ctrl-a`, then `d`, and reattach with:

```bash
screen -r h3-census
```

Use `nohup` only when you do not need an interactive session:

```bash
cd /path/to/istat-census-data
nohup poetry run python scripts/run_h3_census_analysis.py > /home/max/Desktop/census/logs/run_h3_census_analysis_nohup.log 2>&1 &
echo $!
```

`tmux` remains the preferred mode for real-data tests because it keeps the run
interactive, observable, and independent from the IDE process.
