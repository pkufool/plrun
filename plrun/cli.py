#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright  2026 Wei Kang (wkang@pku.edu.cn)
#
# See ../LICENSE for clarification regarding multiple authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import datetime as dt
import sys
import time
import subprocess
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import Manager


_HAS_STDOUT_BUFFER = hasattr(sys.stdout, "buffer")


def get_args(argv=None):
    parser = argparse.ArgumentParser(description="Run commands in parallel.")
    parser.add_argument(
        "-j",
        "--num-jobs",
        type=int,
        default=10,
        help="Number of parallel jobs to run.",
    )
    parser.add_argument(
        "-t",
        "--thread",
        action="store_true",
        help="Use thread pool instead of process pool.",
    )
    parser.add_argument(
        "cmd_file",
        nargs="?",
        default="-",
        help="Command file path, or - for stdin.",
    )
    return parser.parse_args(argv)


def _safe_write_text(lock, stream, text):
    if not text:
        return
    if lock:
        with lock:
            stream.write(text)
            stream.flush()
    else:
        stream.write(text)
        stream.flush()


def _safe_write_bytes(lock, stream, data):
    if not data:
        return
    if lock:
        with lock:
            stream.write(data)
            stream.flush()
    else:
        stream.write(data)
        stream.flush()


def _stream_command(cmd, stream_output, lock):
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    if proc.stdout is None:
        return proc.wait()

    while True:
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        if stream_output:
            if _HAS_STDOUT_BUFFER:
                _safe_write_bytes(lock, sys.stdout.buffer, chunk)
            else:
                _safe_write_text(
                    lock,
                    sys.stdout,
                    chunk.decode("utf-8", errors="replace"),
                )

    proc.stdout.close()
    return proc.wait()


def run_job(job):
    index, cmd, stream_output, lock = job
    start_monotonic = time.monotonic()
    start_wall = dt.datetime.now().isoformat(timespec="seconds")
    rc = 1
    error = None

    try:
        _safe_write_text(
            lock,
            sys.stderr,
            f"[{index}] START {start_wall} CMD: {cmd}\n",
        )
        rc = _stream_command(cmd, stream_output, lock)

        end_wall = dt.datetime.now().isoformat(timespec="seconds")
        duration = time.monotonic() - start_monotonic
        status = "OK" if rc == 0 else "FAIL"
        _safe_write_text(
            lock,
            sys.stderr,
            (
                f"[{index}] END {end_wall} STATUS: {status} "
                f"RC: {rc} DURATION_SEC: {duration:.2f}\n"
            ),
        )
    except Exception as exc:
        error = str(exc)
        duration = time.monotonic() - start_monotonic
        _safe_write_text(
            lock,
            sys.stderr,
            f"[{index}] ERROR {error} DURATION_SEC: {duration:.2f}\n",
        )

    return {
        "index": index,
        "cmd": cmd,
        "returncode": rc,
        "duration": duration,
        "error": error,
    }


def _read_commands(cmd_file):
    if cmd_file == "-":
        return [line.strip() for line in sys.stdin if line.strip()]
    try:
        with open(cmd_file, "r", encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip()]
    except OSError as exc:
        print(
            f"Failed to open command file: {cmd_file} ({exc})",
            file=sys.stderr,
        )
        return None


def _run_jobs(executor_cls, jobs, max_workers):
    with executor_cls(max_workers=max_workers) as pool:
        return list(pool.map(run_job, jobs))


def main(argv=None):
    args = get_args(argv)
    commands = _read_commands(args.cmd_file)
    if commands is None:
        return 1
    if not commands:
        print("No commands provided.", file=sys.stderr)
        return 1

    stream_output = True
    jobs = [
        (index + 1, cmd, stream_output, None)
        for index, cmd in enumerate(commands)
    ]

    if args.thread:
        lock = threading.Lock()
        jobs = [
            (index, cmd, stream_output, lock)
            for index, cmd, stream_output, _ in jobs
        ]
        results = _run_jobs(ThreadPoolExecutor, jobs, args.num_jobs)
    else:
        with Manager() as manager:
            lock = manager.Lock()
            jobs = [
                (index, cmd, stream_output, lock)
                for index, cmd, stream_output, _ in jobs
            ]
            results = _run_jobs(ProcessPoolExecutor, jobs, args.num_jobs)

    success = sum(1 for result in results if result["returncode"] == 0)
    failed = len(results) - success

    print(f"Finished: {success} succeeded, {failed} failed.")
    if failed:
        print("Failed commands:")
        for result in results:
            if result["returncode"] != 0:
                print(
                    f"[{result['index']}] {result['cmd']} "
                    f"(exit {result['returncode']})"
                )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
