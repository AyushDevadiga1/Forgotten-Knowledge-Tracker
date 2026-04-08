# tools/launcher.py — FKT 2.0 Phase 13 fix
# Fixed broken imports: api_server, core.batch_operations never existed.
# Now routes correctly to actual FKT 2.0 modules.

import sys
import os
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # project root


class Launcher:
    def launch_tracker(self, args):
        print("\n  Starting background tracker...")
        subprocess.run([sys.executable, "-m", "tracker_app.main"], cwd=str(ROOT))

    def launch_web(self, args):
        port = getattr(args, "port", None) or 5000
        print(f"\n  Starting dashboard at http://localhost:{port}")
        env = os.environ.copy()
        env["PORT"] = str(port)
        subprocess.run(
            [sys.executable, "-m", "tracker_app.web.app"],
            cwd=str(ROOT), env=env
        )

    def launch_both(self, args):
        print("\n  Starting tracker + dashboard (use Ctrl+C to stop both)...")
        tracker = subprocess.Popen(
            [sys.executable, "-m", "tracker_app.main"], cwd=str(ROOT)
        )
        try:
            subprocess.run(
                [sys.executable, "-m", "tracker_app.web.app"], cwd=str(ROOT)
            )
        finally:
            tracker.terminate()

    def launch_train(self, args):
        print("\n  Training intent classifier...")
        cmd = [sys.executable, "-m", "tracker_app.scripts.train_models_from_logs"]
        if getattr(args, "feedback", False):
            cmd.append("--include-feedback")
        subprocess.run(cmd, cwd=str(ROOT))

    def launch_migrate(self, args):
        print("\n  Running database migrations...")
        subprocess.run(
            [sys.executable, "-m", "tracker_app.db.migrations"],
            cwd=str(ROOT)
        )

    def launch_populate(self, args):
        print("\n  Seeding database with test data...")
        subprocess.run(
            [sys.executable, str(ROOT / "tracker_app" / "tools" / "populate.py")],
            cwd=str(ROOT)
        )

    def launch_check(self, args):
        print("\n  Running error checks...")
        subprocess.run(
            [sys.executable, str(ROOT / "tracker_app" / "check_all_errors.py")],
            cwd=str(ROOT)
        )

    def main(self):
        parser = argparse.ArgumentParser(
            description="FKT 2.0 Launcher",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Commands:
  tracker    Start background tracker
  web        Start dashboard
  both       Start tracker + dashboard together
  train      Retrain intent classifier
  migrate    Apply pending DB migrations
  populate   Seed DB with test data
  check      Run syntax + import checks
            """
        )
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("tracker")

        web_p = sub.add_parser("web")
        web_p.add_argument("--port", type=int, default=5000)

        sub.add_parser("both")

        train_p = sub.add_parser("train")
        train_p.add_argument("--feedback", action="store_true",
                             help="Include user feedback in retraining")

        sub.add_parser("migrate")
        sub.add_parser("populate")
        sub.add_parser("check")

        args   = parser.parse_args()
        routes = {
            "tracker":  self.launch_tracker,
            "web":      self.launch_web,
            "both":     self.launch_both,
            "train":    self.launch_train,
            "migrate":  self.launch_migrate,
            "populate": self.launch_populate,
            "check":    self.launch_check,
        }

        if args.command in routes:
            routes[args.command](args)
        else:
            parser.print_help()


if __name__ == "__main__":
    Launcher().main()
