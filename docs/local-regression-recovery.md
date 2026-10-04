# Reproducing the controlled local regression

This experiment compares two compiled worker variants from one source revision
and restores the exact original Docker image. It demonstrates diagnostic evidence
and artifact recovery in a disposable local lab. GitOps promotion/rollback on
Config Sync or Flux is a separate cloud milestone.

The baseline performs one analysis pass. The experimental regressed build performs
64 identical passes and returns the same report. The variant is a build argument
embedded in the binary, recorded in its image label and exposed as a bounded info
metric. No HTTP endpoint can change it.

## Run

Start a fresh dedicated report-workshop project with the tracing extension:

```sh
cd workload
export APP_REVISION="$(git rev-parse HEAD)"
docker compose -f compose.yaml -f compose.tracing.yaml --profile observability up --build -d
python3 -m pip install jsonschema==4.23.0
python3 evidence/regression.py --revision "$APP_REVISION"
python3 evidence/validate_regression.py output/regression-recovery.json
go tool pprof -top output/baseline-cpu.pprof
go tool pprof -top output/regressed-cpu.pprof
go tool pprof -top output/recovered-cpu.pprof
docker compose -f compose.yaml -f compose.tracing.yaml --profile observability down
```

The runner changes only this project's worker image/tag and recreates that worker.
Use it in a disposable lab with no concurrent runs. It refuses other project names
and unexpected image tags. A final recovery path restores the original image even
after a failed phase; CI's final cleanup owns removal of the whole local project.
If forcibly killed, inspect the worker variant/image before resuming.

## Predeclared protocol

Each phase warms up with two batch-v1 jobs, then measures 12 sequential jobs.
Requests use the same deterministic fixture and algorithm, with no overlapping
submitted jobs in the measured sequence. Five-second CPU profiles are captured
during each phase. Report counts/hash must match for every job:

- 2 documents, 60,000 tokens, 6 unique tokens, no duplicate documents.
- Fixture SHA-256: `0f237c6f846e4f742fb9a0b89195b8f76dbd269470edb28e786c999eb15b91de`.

Accepted-to-completed durations come from database timestamps. Regression must
raise the median by at least 1.5× and 0.05 seconds. Recovery must remain within
2× baseline plus 0.1 seconds of polling jitter. These tolerances are deliberately
coarse for a shared CI runner and a worker with a 200ms polling interval.
They are fixed before the run and preserved in its record.

The recovered image ID must equal the baseline ID; the regressed ID must differ.
Schemas and semantic validation reject missing phases, changed reports, fabricated
medians, invalid phase order, failed recovery and thresholds that were not met.
Profile files must match their recorded lengths and SHA-256 hashes.

This is a closed-loop, sequential investigation with one run per variant. It
does not measure saturation, independent repeated trials, profiling overhead,
customer impact or cross-cloud performance. CPU profiles are aggregate samples;
the trace-to-profile bridge and continuous Pyroscope ingestion remain pending.
Local Docker image IDs are recorded; signed published registry digests are later
release work.

## Following the story

Use the retained run to connect changed computation to its profile/latency, then
compare the recovered original artifact. The earlier local trace/profile check
connects submission, durable storage and worker processing in Tempo, with matching
log IDs. Future Labs ingestion will present these as dated local observations and
will use separate qualified bundles for cloud reconciliation and teardown.
