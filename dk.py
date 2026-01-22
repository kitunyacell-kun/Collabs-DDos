import argparse
import asyncio                                                                                                                                       import time
import sys                                                                                                                                           from typing import Optional
import aiohttp                                                                                                                                       from rich.console import Console                                                                                                                     from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich import print as rprint

class Result:
    def __init__(self, status_code: Optional[int] = None, duration: Optional[float] = None, error: Optional[Exception] = None):
        self.status_code = status_code                                                                                                                       self.duration = duration
        self.error = error

async def make_request(session: aiohttp.ClientSession, url: str, verbose: bool, index: int) -> Result:
    start = time.perf_counter()
    try:
        async with session.get(url) as resp:
            status = resp.status
            # Discard body
            await resp.read()
            duration = time.perf_counter() - start
            if verbose:
                rprint(f"[green]Request {index+1}: HTTP Status Code {status} (Duration: {duration:.3f}s)[/green]")
            return Result(status_code=status, duration=duration)
    except Exception as e:
        duration = time.perf_counter() - start
        if verbose:
            rprint(f"[red]Request {index+1}: Error - {e} (Duration: {duration:.3f}s)[/red]")
        return Result(error=e, duration=duration)

async def run_requests(session: aiohttp.ClientSession, args, progress: Progress, task_id: int) -> tuple[int, int, float]:
    success = 0
    failed = 0
    total_time = 0.0
    index = 0
    start_time = time.perf_counter()

    while True:
        if args.duration and (time.perf_counter() - start_time) >= args.duration:
            break
        if not args.duration and index >= args.requests:
            break

        res = await make_request(session, args.url, args.verbose, index)
        index += 1
        progress.update(task_id, advance=1)

        if res.error:
            failed += 1
        else:
            if 200 <= res.status_code < 300:
                success += 1
                total_time += res.duration
            else:
                failed += 1

        # Rate limiting if needed, but for flooder, full speed
        await asyncio.sleep(0)  # Yield control

    return success, failed, total_time

async def main_async(args):
    console = Console()

    # Print professional header
    header = Panel(
        "[bold blue]Phantom Flooder[/bold blue]\n"
        "Efficient load testing with asyncio and aiohttp\n"
        f"Target: {args.url}\n"
        f"Concurrency: {args.concurrency}\n"
        f"Timeout: {args.timeout}s\n"
        f"{'Duration: ' + str(args.duration) + 's' if args.duration else 'Requests: ' + str(args.requests)}",
        title="War Panel",
        border_style="green",
        expand=False
    )
    console.print(header)

    timeout = aiohttp.ClientTimeout(total=args.timeout)
    connector = aiohttp.TCPConnector(limit=args.concurrency)  # Limit concurrent connections
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            if args.duration:
                total_tasks = args.concurrency  # For duration, we don't know total requests
                task_ids = [progress.add_task(f"Engine {i+1}", total=None) for i in range(args.concurrency)]
            else:
                total_requests = args.requests
                requests_per_worker = (total_requests + args.concurrency - 1) // args.concurrency
                task_ids = [progress.add_task(f"Engine {i+1}", total=requests_per_worker) for i in range(args.concurrency)]

            start_time = time.perf_counter()

            # Run workers
            workers = []
            for i in range(args.concurrency):
                workers.append(run_requests(session, args, progress, task_ids[i]))

            results = await asyncio.gather(*workers)

            total_success = sum(s for s, _, _ in results)
            total_failed = sum(f for _, f, _ in results)
            total_time_sum = sum(t for _, _, t in results)
            total_requests_done = total_success + total_failed

    total_duration = time.perf_counter() - start_time

    # Calculate stats
    avg_time = total_time_sum / total_success if total_success > 0 else 0
    success_rate = (total_success / total_requests_done) * 100 if total_requests_done > 0 else 0
    rps = total_requests_done / total_duration if total_duration > 0 else 0


^G Help         ^O Write Out    ^F Where Is     ^K Cut          ^T Execute      ^C Location     M-U Undo        M-A Set Mark    M-] To Bracket
^X Exit         ^R Read File    ^\ Replace      ^U Paste
