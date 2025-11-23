"""Main entry point for the Job Agent System."""
import argparse
import sys
from orchestrator import JobAgentOrchestrator
from utils import log

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Job Matching System for profesia.sk"
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode with sample data'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )

    args = parser.parse_args()

    try:
        # Initialize orchestrator
        orchestrator = JobAgentOrchestrator(config_path=args.config)

        # Run workflow
        if args.test:
            orchestrator.run_test_mode()
        else:
            orchestrator.run()

    except KeyboardInterrupt:
        log.warning("\nWorkflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        log.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
