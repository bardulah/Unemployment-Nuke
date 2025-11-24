"""Scheduler for running the job agent system daily."""
import schedule
import time
from datetime import datetime
from orchestrator import JobAgentOrchestrator
from utils import log

def run_job_agent():
    """Run the job agent workflow."""
    log.info(f"\n{'='*60}")
    log.info(f"SCHEDULED RUN STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"{'='*60}\n")

    try:
        orchestrator = JobAgentOrchestrator()
        orchestrator.run()

        log.info(f"\n{'='*60}")
        log.info(f"SCHEDULED RUN COMPLETED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"{'='*60}\n")

    except Exception as e:
        log.error(f"Error in scheduled run: {e}")

def main():
    """Main scheduler loop."""
    log.info("Job Agent Scheduler Started")
    log.info("Will run daily at 09:00 AM")

    # Schedule the job to run every day at 9 AM
    schedule.every().day.at("09:00").do(run_job_agent)

    # You can also schedule multiple times per day:
    # schedule.every().day.at("09:00").do(run_job_agent)
    # schedule.every().day.at("18:00").do(run_job_agent)

    # Or run every N hours:
    # schedule.every(6).hours.do(run_job_agent)

    # Run once immediately for testing
    log.info("Running initial check...")
    run_job_agent()

    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nScheduler stopped by user")
