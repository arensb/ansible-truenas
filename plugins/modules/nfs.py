#!/usr/bin/python
__metaclass__ = type

# XXX - Options
# - servers(int, 1-256): number of nfsd servers
# - udp (bool)
# - allow_nonroot (bool)
# x v4 (bool)
# - v4_v3owner (bool)
# - v4_krb (bool)
# - v4_domain (str)
# - bindip (list of ip addrs)
# - mountd_port (int)
# - rpclockd_port (int)
# - usersd_manage_gids (bool)
# - mountd_log (bool)
# - statd_lockd_log (bool)

DOCUMENTATION = '''
---
module: nfs
short_description: Configure NFS service
description:
  - Configure the NFS service.
  - For individual NFS exports, see C(sharing_nfs)
options:
  nfsv4:
    description:
      - If true, enable NFSv4. Otherwise, use NFSv3.
    type: bool
  v3owner:
    description:
      - Enable the NFSv3 ownership model for NFSv4.
version_added: 0.4.0
'''

# XXX
EXAMPLES = '''
- name: Enable NFSv4
  hosts: nfs_server
  become: yes
  tasks:
    - arensb.truenas.nfs:
        nfsv4: yes
'''

# XXX
RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW


def main():
    module = AnsibleModule(
        argument_spec=dict(
            nfsv4=dict(type='bool'),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    nfsv4 = module.params['nfsv4']

    # XXX - Look up the resource
    try:
        nfs_info = mw.call("nfs.config")
    except Exception as e:
        module.fail_json(msg=f"Error looking up nfs configuration: {e}")

    # Make list of differences between what is and what should
    # be.
    arg = {}

    if nfsv4 is not None and nfs_info['v4'] != nfsv4:
        arg['v4'] = nfsv4

    # If there are any changes, nfs.update()
    if len(arg) == 0:
        # No changes
        result['changed'] = False
    else:
        #
        # Update nfs.
        #
        if module.check_mode:
            result['msg'] = f"Would have updated nfs: {arg}"
        else:
            try:
                err = mw.call("nfs.update",
                              arg)
            except Exception as e:
                module.fail_json(msg=f"Error updating nfs with {arg}: {e}")
                # Return any interesting bits from err
                result['status'] = err['status']
        result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
