import importlib.util
import io
import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('wait_for_ci', Path(__file__).with_name('wait_for_ci.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
SHA = 'a' * 40


class Response(io.BytesIO):
    def __init__(self, status, conclusion):
        super().__init__(json.dumps({'workflow_runs': [{'head_sha': SHA, 'head_branch': 'main', 'event': 'push', 'status': status, 'conclusion': conclusion}]}).encode())


class GateTests(TestCase):
    def test_success_requires_exact_current_commit(self):
        with patch.dict(gate.os.environ, {'CONTEXT': 'production', 'COMMIT_REF': SHA}, clear=True), \
             patch.object(gate, 'urlopen', return_value=Response('completed', 'success')), \
             patch.object(gate.subprocess, 'check_output', return_value=SHA + '\trefs/heads/main\n'):
            gate.main()

    def test_failed_ci_and_stale_commits_do_not_publish(self):
        with patch.dict(gate.os.environ, {'CONTEXT': 'production', 'COMMIT_REF': SHA}, clear=True):
            with patch.object(gate, 'urlopen', return_value=Response('completed', 'failure')):
                with self.assertRaises(RuntimeError): gate.main()
            with patch.object(gate, 'urlopen', return_value=Response('completed', 'success')), \
                 patch.object(gate.subprocess, 'check_output', return_value='b' * 40 + '\trefs/heads/main\n'):
                with self.assertRaises(RuntimeError): gate.main()

    def test_nonproduction_does_not_wait(self):
        with patch.dict(gate.os.environ, {'CONTEXT': 'deploy-preview'}, clear=True), \
             patch.object(gate, 'urlopen') as request:
            gate.main()
            request.assert_not_called()


if __name__ == '__main__':
    main()
