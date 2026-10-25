"""Reproduce public checks, independent tests, route calls and benchmark evidence."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'tests'


def run(command, timeout, output_path=None):
    print('$ ' + subprocess.list2cmdline(command), flush=True)
    started = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, text=True, encoding='utf-8',
                            capture_output=True, timeout=timeout)
    if output_path:
        if result.returncode == 0 and output_path.suffix == '.json':
            json.loads(result.stdout)  # Do not save malformed JSON evidence.
        output_path.write_text(result.stdout if output_path.suffix == '.json'
                               else result.stdout + result.stderr, encoding='utf-8')
    if result.stdout:
        print(result.stdout, end='' if result.stdout.endswith('\n') else '\n', flush=True)
    if result.stderr:
        print(result.stderr, end='' if result.stderr.endswith('\n') else '\n', file=sys.stderr, flush=True)
    if result.returncode:
        raise RuntimeError(f'Command failed with exit code {result.returncode}')
    return {'command': command, 'passed': True, 'elapsed_seconds': time.perf_counter() - started}


def main():
    # JAVA_HOME is optional; no machine-specific JDK path is kept in the project.
    if os.environ.get('JAVA_HOME'):
        os.environ['PATH'] = str(Path(os.environ['JAVA_HOME']) / 'bin') + os.pathsep + os.environ.get('PATH', '')
    for executable in ('java', 'javac'):
        if not shutil.which(executable):
            raise RuntimeError(f'{executable} is missing. Put JDK 17+ on PATH or set JAVA_HOME.')
    scratch = ROOT / '.build' / 'test-tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    for name in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[name] = str(scratch)
    commands = []
    commands.append(run([sys.executable, 'tools/run.py', '--setup'], 90, FOLDER / 'setup_results.txt'))
    commands.append(run([sys.executable, 'tools/run.py', '--check'], 180, FOLDER / 'public_results.txt'))
    commands.append(run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_*.py'], 180,
                        FOLDER / 'tool_tests_results.txt'))
    commands.append(run([sys.executable, 'tests/verify.py'], 300, FOLDER / 'own_results.txt'))
    commands.append(run(['javac', '--release', '17', '-encoding', 'UTF-8', '-cp', '.build/Java',
                         '-d', '.build/Java', 'tests/AlgorithmChecks.java'], 60))
    commands.append(run(['java', '-Xmx384m', '-cp', '.build/Java', 'AlgorithmChecks'], 60,
                        FOLDER / 'route_results.json'))
    commands.append(run(['java', '-Xmx384m', '-cp', '.build/Java', 'AlgorithmChecks', 'benchmark'], 180,
                        FOLDER / 'benchmark_results.json'))
    files = ['src/Java/Algorithms.java', 'src/Java/Input.java', 'src/Java/Json.java', 'src/Java/Main.java',
             'submission.json', 'tests/verify.py', 'tests/AlgorithmChecks.java', 'tests/run_all.py']
    report = {
        'executed_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'platform': platform.platform(),
        'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
        'commands': commands, 'all_passed': True
    }
    (FOLDER / 'run_manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PASS complete verification and benchmark', flush=True)


if __name__ == '__main__':
    main()
