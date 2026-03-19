# plrun

Run shell commands in parallel.

## Install

pip install plrun

## Usage

```
$ plrun -h

usage: plrun [-h] [-j NUM_JOBS] [cmd_file]

Run commands in parallel.

positional arguments:
  cmd_file              Command file path, or - for stdin.

optional arguments:
  -h, --help            show this help message and exit
  -j NUM_JOBS, --num-jobs NUM_JOBS
                        Number of parallel jobs to run.

$ printf "echo hello world\nsleep 1\nsleep 2\n" | plrun -j 3

[1] START 2026-03-18T19:12:24 CMD: echo hello world
[2] START 2026-03-18T19:12:24 CMD: sleep 1
[3] START 2026-03-18T19:12:24 CMD: sleep 2
hello world
[1] END 2026-03-18T19:12:24 STATUS: OK RC: 0 DURATION_SEC: 0.00
[2] END 2026-03-18T19:12:25 STATUS: OK RC: 0 DURATION_SEC: 1.02
[3] END 2026-03-18T19:12:26 STATUS: OK RC: 0 DURATION_SEC: 2.04
Finished: 3 succeeded, 0 failed.
```