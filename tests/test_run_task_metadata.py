from kkrunner import RunStore
from kkrunner.runs.manager import RunManager


def test_run_record_persists_task_and_schema(tmp_path):
    manager = RunManager(RunStore(tmp_path / "runs"))
    record = manager.new_record(
        directory=tmp_path, metadata={"test": {"task": "SPLEED", "input_definition": "ARPES"}}, processing_required=True
    )
    manager.store.save(record)
    loaded = manager.store.get(record.id)
    assert loaded.metadata["test"]["task"] == "SPLEED"
    assert loaded.metadata["test"]["input_definition"] == "ARPES"
    assert not hasattr(loaded, "requested_task")
