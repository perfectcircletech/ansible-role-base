from ansible.module_utils.basic import AnsibleModule
import subprocess
import os
import shutil
import re
import hashlib
import fcntl
import time

# - name: Determine rsync connection method
#   set_fact:
#     rsync_rsh: >-
#       {%- if ansible_connection == 'docker' or ansible_connection == 'community.docker.docker' -%}
#       docker exec -i
#       {%- elif ansible_connection == 'ssh' or ansible_connection == 'paramiko_ssh' -%}
#       {{ lookup('env', 'RSYNC_RSH') | default('ssh -o HostKeyAlgorithms=ssh-ed25519 -o PreferredAuthentications=publickey -o StrictHostKeyChecking=yes', True) }}
#       {%- else -%}
#       ssh
#       {%- endif -%}
#     rsync_host: >-
#       {%- if ansible_connection == 'docker' or ansible_connection == 'community.docker.docker' -%}
#       {{ inventory_hostname }}:
#       {%- else -%}
#       {{ ansible_host | default(inventory_hostname) }}:
#       {%- endif -%}

# - name: Sync user profile from git module
#   git_profile_sync:
#     repo: "{{ user.profile_repo }}"
#     dest: "{{ rsync_host }}/home/{{ user.name }}"
#     uid: "{{ user.uid | default(user.name) }}"
#     gid: "{{ user.gid | default(user.name) }}"
#     branch: "{{ user.branch | default('master') }}"
#     rsync_opts:
#       - "-av"
#       - "--update"
#       - "--omit-dir-times"
#       - "--rsh={{ rsync_rsh }}"
#       - "--chmod=u=rwX,g=,o="
#       - "--chown={{ user.uid | default(user.name) }}:{{ user.gid |
#         default(user.name) }}"
#   delegate_to: localhost
#   become: false

# - name: Set owner
#   ansible.builtin.file:
#     path: "/home/{{ user.name }}"
#     state: directory
#     owner: "{{ user.uid | default(user.name) }}"
#     group: "{{ user.gid | default(user.name) }}"


def run_command(cmd, cwd=None, env=None):
  process_env = os.environ.copy()
  if env:
    process_env.update(env)
  process = subprocess.Popen(
    cmd, cwd=cwd, env=process_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
  )
  stdout, stderr = process.communicate()
  return process.returncode, stdout.decode('utf-8'), stderr.decode('utf-8')


def get_repo_hash(repo_url):
  return hashlib.md5(repo_url.encode('utf-8')).hexdigest()[:12]


def acquire_lock(lock_file, timeout=300):
  start_time = time.time()
  lock_fd = open(lock_file, 'w')
  while True:
    try:
      fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
      return lock_fd
    except IOError:
      if time.time() - start_time > timeout:
        lock_fd.close()
        return None
      time.sleep(0.1)


def release_lock(lock_fd):
  if lock_fd:
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()


def prepare_staging_dir(repo_url, staging_base):
  repo_hash = get_repo_hash(repo_url)
  staging_dir = os.path.join(staging_base, f'profile_{repo_hash}')
  if os.path.exists(staging_dir):
    if not os.path.exists(os.path.join(staging_dir, '.git')):
      shutil.rmtree(staging_dir)
      os.makedirs(staging_dir, mode=0o700)
  else:
    os.makedirs(staging_dir, mode=0o700)
  return staging_dir


def sync_repo(repo_url, staging_dir, branch='master', git_ssh_opts=''):
  git_env = {}
  if git_ssh_opts:
    git_env['GIT_SSH_COMMAND'] = f'ssh {git_ssh_opts}'
  if os.path.exists(os.path.join(staging_dir, '.git')):
    cmd = ['git', 'pull', 'origin', branch]
    rc, stdout, stderr = run_command(cmd, cwd=staging_dir, env=git_env)
    if rc != 0:
      return False, stderr
    return True, "Repository updated"
  else:
    cmd = ['git', 'clone', '--branch', branch, repo_url, staging_dir]
    rc, stdout, stderr = run_command(cmd, env=git_env)
    if rc != 0:
      return False, stderr
    return True, "Repository cloned"


def restore_timestamps(repo_path):
  cmd = ['git', 'log', '--pretty=%at', '--name-status', '--reverse']
  rc, stdout, stderr = run_command(cmd, cwd=repo_path)
  if rc != 0:
    return False, stderr
  seen = {}
  current_timestamp = None
  for line in stdout.split('\n'):
    line = line.strip()
    if not line:
      continue
    parts = line.split(None, 1)
    if len(parts) == 1:
      try:
        current_timestamp = int(parts[0])
      except ValueError:
        continue
      continue
    if len(parts) == 2 and current_timestamp is not None:
      status, filename = parts
      if filename in seen:
        continue
      if re.match(r'[AM]', status):
        filepath = os.path.join(repo_path, filename)
        if os.path.exists(filepath):
          try:
            os.utime(filepath, (current_timestamp, current_timestamp))
            seen[filename] = True
          except OSError:
            pass
  return True, "Timestamps restored"


def check_real_changes(rsync_output):
  lines = rsync_output.strip().split('\n')

  has_changes = False
  for line in lines:
    line = line.strip()
    if not line:
      continue
    if line.startswith('sending incremental file list'):
      continue
    if line.startswith('sent ') or line.startswith('total size'):
      continue
    if line.startswith('.git/') or line == '.git':
      continue
    has_changes = True
    break

  return has_changes


def sync_files(src, dest, rsync_opts):
  rsync_cmd = ['rsync'] + rsync_opts + [f'{src}/.', dest]
  process = subprocess.Popen(rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, stderr = process.communicate()
  if process.returncode != 0:
    return False, f'-----[{rsync_cmd}]-----' + stderr.decode('utf-8')
  return True, f'-----[{rsync_cmd}]-----' + stdout.decode('utf-8')


def main():
  module = AnsibleModule(
    argument_spec=dict(
      repo=dict(type='str', required=True),
      dest=dict(type='str', required=True),
      uid=dict(type='str', required=True),
      gid=dict(type='str', required=True),
      branch=dict(type='str', default='master'),
      git_ssh_opts=dict(type='str', default='-o StrictHostKeyChecking=accept-new'),
      rsync_opts=dict(type='list', elements='str', default=None),
      staging_base=dict(type='str', default='/tmp/ansible_git_profiles'),
      cleanup=dict(type='bool', default=False),
      lock_timeout=dict(type='int', default=300)
    ),
    supports_check_mode=False
  )
  repo = module.params['repo']
  dest = module.params['dest']
  uid = module.params['uid']
  gid = module.params['gid']
  branch = module.params['branch']
  git_ssh_opts = module.params['git_ssh_opts']
  rsync_opts = module.params['rsync_opts']
  staging_base = module.params['staging_base']
  cleanup = module.params['cleanup']
  lock_timeout = module.params['lock_timeout']

  if rsync_opts is None:
    rsync_opts = ['-av', '--update', '--omit-dir-times']
  else:
    rsync_opts = [
      opt.replace('{{uid}}', uid).replace('{{gid}}', gid) for opt in rsync_opts
    ]
  staging_dir = None
  lock_fd = None
  try:
    os.makedirs(staging_base, mode=0o700, exist_ok=True)
    repo_hash = get_repo_hash(repo)
    lock_file = os.path.join(staging_base, f'profile_{repo_hash}.lock')
    lock_fd = acquire_lock(lock_file, lock_timeout)
    if not lock_fd:
      module.fail_json(msg=f"Failed to acquire lock within {lock_timeout} seconds")
    staging_dir = prepare_staging_dir(repo, staging_base)
    success, msg = sync_repo(repo, staging_dir, branch, git_ssh_opts)
    if not success:
      module.fail_json(msg=f"Failed to sync repository: {msg}")
    success, msg = restore_timestamps(staging_dir)
    if not success:
      module.fail_json(msg=f"Failed to restore timestamps: {msg}")
    release_lock(lock_fd)
    lock_fd = None
    success, output = sync_files(staging_dir, dest, rsync_opts)
    if not success:
      module.fail_json(msg=f"Failed to sync files: {output}")
    changed = check_real_changes(output)
    result = {
      'changed': changed,
      'msg': 'Profile synchronized successfully',
      'sync_output': output
    }
    module.exit_json(**result)
  except Exception as e:
    module.fail_json(msg=f"Unexpected error: {str(e)}")
  finally:
    release_lock(lock_fd)
    if cleanup and staging_dir and os.path.exists(staging_dir):
      shutil.rmtree(staging_dir, ignore_errors=True)


if __name__ == '__main__':
  main()
