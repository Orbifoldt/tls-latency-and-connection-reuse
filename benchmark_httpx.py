# Author: GPT-5.6-luna (ofcourse)
"""Compare httpx connection setup with connection reuse.

Run this module while the demo HTTPS server is available, for example:

    uv run python -m client_app.benchmark_httpx --duration 60 --concurrency 10

The reported latency includes creating and closing ``AsyncClient`` for the
``new-client`` strategy.  For ``reused-client``, the client is created once
before the benchmark and shared by all workers.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from dataclasses import dataclass

import httpx


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BenchmarkResult:
    strategy: str
    elapsed_seconds: float
    completed_calls: int
    successful_calls: int
    failed_calls: int
    latencies_ms: list[float]

    @property
    def calls_per_minute(self) -> float:
        return self.completed_calls / self.elapsed_seconds * 60


async def request_with_new_client(
    url: str, verify: str | bool, timeout: float
) -> tuple[float, int | None]:
    """Make one request, including the cost of creating the client."""
    started = time.perf_counter()
    status_code: int | None = None
    try:
        async with httpx.AsyncClient(verify=verify, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            status_code = response.status_code
    except httpx.HTTPError as error:
        LOGGER.warning("new-client request failed: %s", error)
    latency_ms = (time.perf_counter() - started) * 1_000
    return latency_ms, status_code


async def request_with_reused_client(
    client: httpx.AsyncClient, url: str
) -> tuple[float, int | None]:
    """Make one request using an already-created client."""
    started = time.perf_counter()
    status_code: int | None = None
    try:
        response = await client.get(url)
        response.raise_for_status()
        status_code = response.status_code
    except httpx.HTTPError as error:
        LOGGER.warning("reused-client request failed: %s", error)
    latency_ms = (time.perf_counter() - started) * 1_000
    return latency_ms, status_code


async def run_benchmark(
    *,
    strategy: str,
    url: str,
    duration: float,
    concurrency: int,
    verify: str | bool,
    timeout: float,
) -> BenchmarkResult:
    """Run one benchmark strategy until ``duration`` seconds have elapsed."""
    started = time.perf_counter()
    deadline = started + duration
    latencies_ms: list[float] = []
    successful_calls = 0

    client: httpx.AsyncClient | None = None
    if strategy == "reused-client":
        client = httpx.AsyncClient(
            verify=verify,
            timeout=timeout,
            limits=httpx.Limits(max_connections=concurrency),
        )

    async def worker() -> None:
        nonlocal successful_calls
        while time.perf_counter() < deadline:
            if strategy == "new-client":
                latency_ms, status_code = await request_with_new_client(url, verify, timeout)
            else:
                assert client is not None
                latency_ms, status_code = await request_with_reused_client(client, url)

            latencies_ms.append(latency_ms)
            if status_code is not None:
                successful_calls += 1
            LOGGER.debug(
                "strategy=%s status=%s latency_ms=%.2f",
                strategy,
                status_code if status_code is not None else "error",
                latency_ms,
            )

    try:
        await asyncio.gather(*(worker() for _ in range(concurrency)))
    finally:
        if client is not None:
            await client.aclose()

    elapsed_seconds = time.perf_counter() - started
    completed_calls = len(latencies_ms)
    result = BenchmarkResult(
        strategy=strategy,
        elapsed_seconds=elapsed_seconds,
        completed_calls=completed_calls,
        successful_calls=successful_calls,
        failed_calls=completed_calls - successful_calls,
        latencies_ms=latencies_ms,
    )
    log_summary(result)
    return result


def log_summary(result: BenchmarkResult) -> None:
    """Log throughput and latency statistics for one benchmark run."""
    if result.latencies_ms:
        average_ms = sum(result.latencies_ms) / len(result.latencies_ms)
        minimum_ms = min(result.latencies_ms)
        maximum_ms = max(result.latencies_ms)
    else:
        average_ms = minimum_ms = maximum_ms = 0.0

    LOGGER.info(
        "summary strategy=%s calls=%d successful=%d failed=%d "
        "calls_per_minute=%.2f latency_ms(avg/min/max)=%.2f/%.2f/%.2f",
        result.strategy,
        result.completed_calls,
        result.successful_calls,
        result.failed_calls,
        result.calls_per_minute,
        average_ms,
        minimum_ms,
        maximum_ms,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="https://example.com/",
        help="URL to benchmark (default: https://example.com/)",
    )
    parser.add_argument(
        "--duration", type=float, default=60.0, help="Seconds per strategy"
    )
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Concurrent workers"
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="Request timeout in seconds"
    )
    parser.add_argument(
        "--insecure", action="store_true", help="Disable TLS certificate verification"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    args = parser.parse_args()
    if args.duration <= 0 or args.concurrency <= 0 or args.timeout <= 0:
        parser.error("duration, concurrency, and timeout must be greater than zero")
    return args


async def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # ``True`` delegates certificate verification to httpx/httpcore and the
    # operating system's default CA truststore.
    verify = not args.insecure

    for strategy in ("new-client", "reused-client"):
        LOGGER.info(
            "starting strategy=%s duration=%.1fs concurrency=%d",
            strategy,
            args.duration,
            args.concurrency,
        )
        await run_benchmark(
            strategy=strategy,
            url=args.url,
            duration=args.duration,
            concurrency=args.concurrency,
            verify=verify,
            timeout=args.timeout,
        )


if __name__ == "__main__":
    asyncio.run(main())
