"""Scheduler workload intentionally using no scientific application package."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from kkrunner import ExecutionSpec, PsijExecutor, RunState, RunStore
from kkrunner.manager import ExecutionManager


def main():
    with TemporaryDirectory(prefix="kkrunner-slurm-") as work:
        directory = Path(work)
        manager = ExecutionManager(RunStore(directory / "runs"))
        run = manager.create_run(
            PsijExecutor("slurm"),
            ExecutionSpec(
                [sys.executable, "-c", "from pathlib import Path; Path('result.txt').write_text('42'); print('done')"],
                directory=work,
                output_file=directory / "stdout.txt",
                output_files=(directory / "result.txt",),
            ),
        )
        assert run.run().return_code == 0
        assert manager.store.get(run.id).state == RunState.FINISHED
        assert (directory / "result.txt").read_text() == "42"
        assert (directory / "stdout.txt").read_text().strip() == "done"
    print("Standalone KKRunner -> PSI/J -> Slurm passed")


if __name__ == "__main__":
    main()
