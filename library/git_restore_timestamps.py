from ansible.module_utils.basic import AnsibleModule
import subprocess
import re
from pathlib import Path
import os


def run_command(cmd, cwd=None):
  process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, stderr = process.communicate()
  return process.returncode, stdout.decode('utf-8'), stderr.decode('utf-8')


def restore_timestamps(repo_path):
  cmd = ['git', 'log', '--pretty=%at', '--name-status']
  rc, stdout, stderr = run_command(cmd, cwd=str(repo_path))
  if rc != 0:
    return False, stderr, 0
  seen = set()
  current_timestamp = None
  files_changed = 0
  for line in stdout.split('\n'):
    line = line.strip()
    if not line:
      continue
    parts = line.split(None, 1)
    if len(parts) == 1:
      try:
        current_timestamp = int(parts[0])
      except ValueError:
        current_timestamp = None
      continue
    if len(parts) == 2:
      status, filename = parts
      if current_timestamp is None or filename in seen:
        continue
      if re.match(r'[AM]', status):
        filepath = repo_path / filename
        if filepath.exists():
          try:
            current_mtime = int(filepath.stat().st_mtime)
            if current_mtime != current_timestamp:
              os.utime(filepath, (current_timestamp, current_timestamp))
              files_changed += 1
            seen.add(filename)
          except OSError:
            pass
  return True, f"Timestamps restored for {files_changed} files", files_changed


def main():
  module = AnsibleModule(
    argument_spec=dict(path=dict(type='str', required=True)), supports_check_mode=False
  )
  path = Path(module.params['path'])
  if not path.exists():
    module.fail_json(msg=f"Path does not exist: {path}")
  if not (path / '.git').exists():
    module.fail_json(msg=f"Path is not a git repository: {path}")
  try:
    success, msg, files_changed = restore_timestamps(path)
    if not success:
      module.fail_json(msg=f"Failed to restore timestamps: {msg}")
    result = {
      'changed': files_changed > 0,
      'msg': msg,
      'files_changed': files_changed
    }
    module.exit_json(**result)

  except Exception as e:
    module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == '__main__':
  main()
