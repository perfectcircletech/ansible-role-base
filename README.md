# Base role

Role for base configuration the hosts, e.g. users, repos, packages.

| Variable                     | Description                                              | Default                       |
|:----------------------------:|:--------------------------------------------------------:|:-----------------------------:|
| `base_users`                 | List of users                                            | `[]`                          |
| `base_default_packages`      | List of default packages for installation                | [link](defaults/main.yaml#L3) |
| `base_packages`              | List of additional packages for installation             | `[]`                          |
| `base_deny_default_packages` | List of forbidden packages for deinstallation            | `[]`                          |
| `base_deny_packages`         | List of additional forbidden packages for deinstallation | `[]`                          |
| `base_apt_keys`              | List of APT repos keys                                   | `[]`                          |
| `base_apt_repos`             | List of APT repos                                        | `[]`                          |
| `base_resolv_conf_path`      | Destination path of resolv.conf                          | `/etc/resolv.conf`            |
| `base_resolv_nameservers`    | List of nameservers for resolv.conf                      | `['1.1.1.1', '8.8.8.8']`      |
| `base_resolv_search_domains` | List of search domain for resolv.conf                    | `[]`                          |
| `base_resolv_options`        | Options for resolv.conf                                  | `timeout:2 attempts:3`        |

## Example usage

```yaml
- hosts: all
  become: true
  roles:
    - role: perfectcircletech.ansible-role-base
  tags:
    - base
```

```yaml
base_users:
  - name: johndoe
    comment: John Doe
    groups:
      - sudo
    shell: /bin/bash
    create_home: true
    git_profile: johndoe
```

```yaml
base_packages:
  - git
  - nmap
```

```yaml
base_apt_keys:
  - url: https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key
    state: present
```

```yaml
base_apt_repos:
  - repo: "deb https://deb.nodesource.com/node_18.x nodistro main"
    state: present
```

```yaml
base_resolv_nameservers:
  - 192.168.0.1
  - 192.0.2.1
base_resolv_search_domains:
  - example.com
```

## Install

Add role to requirements file

```yaml
roles:
  - name: "perfectcircletech.ansible-role-base"
    src: "git+https://github.com/perfectcircletech/ansible-role-base.git"
    version: "0.1.0"
```

and install via `ansible-galaxy`

```bash
ansible-galaxy install -r roles/requirements.yaml
```

## Testing

Use [molecule](https://ansible.readthedocs.io/projects/molecule/).

### Install to venv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r molecule/requirements.txt
```

#### Testing Example

```bash
molecule test
```

## Linting

Use [ansible-lint](https://ansible.readthedocs.io/projects/lint/) and [yamllint](https://yamllint.readthedocs.io/en/stable/).

### Linting Example

```bash
ansible-lint -v
yamllint .
```
