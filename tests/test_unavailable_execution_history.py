"""Unsupported execution implementations do not make file history corrupt."""

import json

import pytest

from kkrunner import RunManager, RunState, RunStore
from kkrunner.files import FileEntry, FileManifest
from kkrunner.runs import DuplicateSubmissionError


@pytest.mark.parametrize("component", ("backend", "transport"))
@pytest.mark.parametrize("state", (RunState.RUNNING, RunState.FINISHED))
def test_unsupported_execution_remains_browsable_and_preserves_reservations(tmp_path, component, state):
    manager = RunManager(RunStore(tmp_path / "runs"))
    output = tmp_path / "old.out"
    output.write_text("old result")
    files = FileManifest(stdout=FileEntry(str(output)))
    record = manager.new_record(directory=tmp_path, files=files)
    record = manager.transition(record, state=state, execution=record.execution.submitted("old-id"))
    path = next(manager.store.directory.rglob("*.json"))
    data = json.loads(path.read_text())
    if component == "backend":
        settings = {"name": "old-backend", "options": [["old-option", "value"]]}
    else:
        settings = {"kind": "old-connection", "host": "old-host", "old-option": "value"}
    data["execution"][component] = settings
    path.write_text(json.dumps(data))

    loaded = manager.store.get(record.id)
    assert not loaded.execution.available
    assert manager.store.runs() == (loaded,)
    assert manager.output_file_is_current(loaded)
    if state.is_terminal:
        assert manager.retrieve_result_files(loaded) == loaded
    assert manager.refresh((loaded,)) == (loaded,)
    manager.store.save(loaded)
    assert json.loads(path.read_text())["execution"][component] == settings
    with pytest.raises(ValueError, match="Unsupported"):
        manager.client_for(loaded)

    unrelated = manager.new_record(directory=tmp_path / "unrelated")
    assert manager.reserve(unrelated).state == RunState.SUBMITTING
    competing = manager.new_record(directory=tmp_path, files=files)
    if not state.is_terminal:
        with pytest.raises(DuplicateSubmissionError):
            manager.reserve(competing)
    else:
        assert manager.reserve(competing).state == RunState.SUBMITTING
