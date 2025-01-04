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

## Example usage

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

## Testing

Use [molecule](https://ansible.readthedocs.io/projects/molecule/)

#### Install to venv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r molecule/requirements.txt
```

#### Example

```bash
molecule test
```
