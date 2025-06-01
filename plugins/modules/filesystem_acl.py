#!/usr/bin/python
__metaclass__ = type

DOCUMENTATION = """
---
module: filesystem_acl
short_description: Manage filesystem ACLs (NFS4 or POSIX1E) on TrueNAS
description:
  - This module allows you to manage filesystem ACLs for a specific path on TrueNAS.
  - Supports NFS4 and POSIX1E ACLs, as well as additional flags and options.
  - Expands any 'BASIC' permission shortcuts (e.g. FULL_CONTROL, READ) into the boolean
    permissions that TrueNAS sets, ensuring idempotency on subsequent runs.
options:
  path:
    description:
      - Path to the file or directory where the ACL should be managed.
    type: str
    required: true

  username:
    description:
      - Name of the user who will own the path (mutually exclusive with C(uid)).
      - If provided, the module looks up the numeric UID via user.get_user_obj.
    type: str
    required: false
    default: null

  uid:
    description:
      - Numeric user ID of the path owner (mutually exclusive with C(username)).
    type: int
    required: false
    default: null

  groupname:
    description:
      - Name of the group that will own the path (mutually exclusive with C(gid)).
      - If provided, the module looks up the numeric GID via group.get_group_obj.
    type: str
    required: false
    default: null

  gid:
    description:
      - Numeric group ID of the path group (mutually exclusive with C(groupname)).
    type: int
    required: false
    default: null

  dacl_nfs4:
    description:
      - List of NFS4 ACL entries. Only relevant if C(acltype=NFS4).
    type: list
    elements: dict
    required: false
    default: []
    suboptions:
      tag:
        description:
          - Type of the ACL entry (e.g. owner@, USER, etc.).
        type: str
        choices:
          - owner@
          - group@
          - everyone@
          - USER
          - GROUP
      username:
        description:
          - If I(tag=USER), specify a username instead of numeric ID.
          - Mutually exclusive with I(id).
        type: str
        default: null
      groupname:
        description:
          - If I(tag=GROUP), specify a group name instead of numeric ID.
          - Mutually exclusive with I(id).
        type: str
        default: null
      id:
        description:
          - If I(tag=USER) or I(tag=GROUP), numeric ID of the user or group.
        type: int
        default: null
      type:
        description:
          - ALLOW or DENY
        type: str
        choices:
          - ALLOW
          - DENY
      perms:
        description:
          - Fine-grained permissions for the ACL entry.
        type: dict
        default: {}
        suboptions:
          READ_DATA:
            type: bool
            default: false
          WRITE_DATA:
            type: bool
            default: false
          APPEND_DATA:
            type: bool
            default: false
          READ_NAMED_ATTRS:
            type: bool
            default: false
          WRITE_NAMED_ATTRS:
            type: bool
            default: false
          EXECUTE:
            type: bool
            default: false
          DELETE_CHILD:
            type: bool
            default: false
          READ_ATTRIBUTES:
            type: bool
            default: false
          WRITE_ATTRIBUTES:
            type: bool
            default: false
          DELETE:
            type: bool
            default: false
          READ_ACL:
            type: bool
            default: false
          WRITE_ACL:
            type: bool
            default: false
          WRITE_OWNER:
            type: bool
            default: false
          SYNCHRONIZE:
            type: bool
            default: false
          BASIC:
            description:
              - Shortcut for sets of permissions (FULL_CONTROL, MODIFY, READ, TRAVERSE).
              - The module expands this into the boolean bits that TrueNAS stores.
            type: str
            choices:
              - FULL_CONTROL
              - MODIFY
              - READ
              - TRAVERSE
      flags:
        description:
          - Inheritance flags for NFS4 ACL entry.
        type: dict
        default: {}
        suboptions:
          FILE_INHERIT:
            type: bool
            default: false
          DIRECTORY_INHERIT:
            type: bool
            default: false
          NO_PROPAGATE_INHERIT:
            type: bool
            default: false
          INHERIT_ONLY:
            type: bool
            default: false
          INHERITED:
            type: bool
            default: false
          BASIC:
            description:
              - Shortcut for flags (INHERIT, NOINHERIT).
            type: str
            choices:
              - INHERIT
              - NOINHERIT

  dacl_posix:
    description:
      - List of POSIX1E ACL entries. Only relevant if C(acltype=POSIX1E).
    type: list
    elements: dict
    required: false
    default: []
    suboptions:
      default:
        type: bool
        default: false
      tag:
        type: str
        choices:
          - USER_OBJ
          - GROUP_OBJ
          - USER
          - GROUP
          - OTHER
          - MASK
      username:
        description:
          - If I(tag=USER), specify a username instead of numeric ID.
          - Mutually exclusive with I(id).
        type: str
        default: null
      groupname:
        description:
          - If I(tag=GROUP), specify a group name instead of numeric ID.
          - Mutually exclusive with I(id).
        type: str
        default: null
      id:
        type: int
        default: -1
      perms:
        description:
          - POSIX1E read/write/execute permissions.
        type: dict
        default: {}
        suboptions:
          READ:
            type: bool
            default: false
          WRITE:
            type: bool
            default: false
          EXECUTE:
            type: bool
            default: false

  nfs41_flags:
    description:
      - Additional flags (autoinherit, protected, etc.) relevant if I(acltype=NFS4).
    type: dict
    default: {}
    suboptions:
      autoinherit:
        type: bool
        default: false
      protected:
        type: bool
        default: false
      defaulted:
        type: bool
        default: false

  acltype:
    description:
      - Which ACL type is used (NFS4, POSIX1E, or DISABLED).
    type: str
    choices:
      - NFS4
      - POSIX1E
      - DISABLED
    default: null

  options:
    description:
      - Additional options for applying the ACL.
    type: dict
    default: {}
    suboptions:
      stripacl:
        type: bool
        default: false
      recursive:
        type: bool
        default: false
      traverse:
        type: bool
        default: false
      canonicalize:
        type: bool
        default: true
      validate_effective_acl:
        type: bool
        default: true

version_added: "1.0.0"
author:
  - Your Name (@your_github_handle)
"""

EXAMPLES = """
- name: Set an NFS4 ACL with name-based lookups
  filesystem_acl:
    path: /mnt/test-expansion/chunkr3
    acltype: NFS4

    # top-level ownership
    username: root
    groupname: smb_users2

    # NFS4 ACL entries with name-based lookups and BASIC perms
    dacl_nfs4:
      - tag: USER
        username: root
        type: ALLOW
        perms:
          BASIC: FULL_CONTROL
        flags:
          BASIC: INHERIT

      - tag: GROUP
        groupname: smb_users
        type: ALLOW
        perms:
          BASIC: READ
        flags:
          BASIC: INHERIT

      - tag: GROUP
        groupname: smb_users2
        type: DENY
        perms:
          BASIC: FULL_CONTROL
        flags:
          BASIC: INHERIT

    options:
      recursive: true
"""

RETURN = """
changed:
  description: Boolean indicating whether any changes were made.
  returned: always
  type: bool
msg:
  description: A message indicating what was changed, or that no change was needed.
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
import json

# from ansible_collections.arensb.truenas.plugins.module_utils.middleware import MiddleWare as MW
# from ansible_collections.arensb.truenas.plugins.module_utils.midclt import Midclt
from ..module_utils.middleware import MiddleWare as MW
from ..module_utils.midclt import Midclt


def strip_default_values(params, arg_spec):
    if not isinstance(arg_spec, dict):
        return params

    if arg_spec.get("type") == "dict" and "options" in arg_spec:
        if not isinstance(params, dict):
            return params

        cleaned = {}
        for key, option_spec in arg_spec["options"].items():
            if key in params:
                value = params[key]
                new_value = strip_default_values(value, option_spec)

                if "default" in option_spec:
                    default_val = option_spec["default"]
                    if new_value == default_val:
                        continue
                cleaned[key] = new_value
        return cleaned

    if arg_spec.get("type") == "list":
        if not isinstance(params, list):
            return params

        element_type = arg_spec.get("elements")
        if element_type == "dict" and "options" in arg_spec:
            new_list = []
            for item in params:
                new_item = strip_default_values(
                    item, {"type": "dict", "options": arg_spec["options"]}
                )
                new_list.append(new_item)
            return new_list
        else:
            return params

    return params


def has_object_changed(d1, d2):
    """
    Recursively compare d1 and d2, ignoring list order by sorting them
    as JSON strings. If there's any difference, return True.
    """
    if type(d1) != type(d2):
        return True

    if isinstance(d1, dict):
        if set(d1.keys()) != set(d2.keys()):
            return True
        for k in d1:
            if has_object_changed(d1[k], d2[k]):
                return True
        return False

    if isinstance(d1, list):
        if len(d1) != len(d2):
            return True
        # Sort by JSON so it's deterministic
        sorted_d1 = sorted(d1, key=lambda x: json.dumps(x, sort_keys=True))
        sorted_d2 = sorted(d2, key=lambda x: json.dumps(x, sort_keys=True))
        for i in range(len(sorted_d1)):
            if has_object_changed(sorted_d1[i], sorted_d2[i]):
                return True
        return False

    return d1 != d2


def convert_acl_entry_names(mw, acl_entries, is_nfs4=True):
    """
    For each ACL entry:
      - If tag=USER + username => look up numeric id via user.get_user_obj
      - If tag=GROUP + groupname => look up numeric id via group.get_group_obj
      - Store into entry["id"]
    """
    for entry in acl_entries:
        tag = entry.get("tag")
        if tag == "USER" and entry.get("username"):
            if entry.get("id") not in [None, -1]:
                raise ValueError(
                    f"ACL entry has both 'username' and 'id' for tag=USER: {entry}"
                )
            try:
                user_info = mw.call(
                    "user.get_user_obj", {"username": entry["username"]}
                )
            except Exception as err:
                raise ValueError(f"Failed user lookup '{entry['username']}': {err}")
            if not user_info or "pw_uid" not in user_info:
                raise ValueError(f"User lookup invalid data: {user_info}")
            entry["id"] = user_info["pw_uid"]

        elif tag == "GROUP" and entry.get("groupname"):
            if entry.get("id") not in [None, -1]:
                raise ValueError(
                    f"ACL entry has both 'groupname' and 'id' for tag=GROUP: {entry}"
                )
            try:
                group_info = mw.call(
                    "group.get_group_obj", {"groupname": entry["groupname"]}
                )
            except Exception as err:
                raise ValueError(f"Failed group lookup '{entry['groupname']}': {err}")
            if not group_info or "gr_gid" not in group_info:
                raise ValueError(f"Group lookup invalid data: {group_info}")
            entry["id"] = group_info["gr_gid"]


def cleanup_nfs4_aces_for_setacl(aces):
    """
    1) Expand BASIC perms & flags so that final 'perms' matches what TrueNAS returns.
    2) Remove ephemeral keys (username, groupname).
    """
    for ace in aces:
        ace.pop("username", None)
        ace.pop("groupname", None)


def cleanup_posix_aces_for_setacl(aces):
    """
    Remove fields not recognized by posix1e_ace. Only keep READ/WRITE/EXECUTE in perms.
    Remove 'type', 'flags', 'username', 'groupname', or any NFS4 bits.
    """
    for ace in aces:
        ace.pop("username", None)
        ace.pop("groupname", None)
        ace.pop("type", None)
        ace.pop("flags", None)
        # Keep only {READ, WRITE, EXECUTE} in perms
        posix_ok = ("READ", "WRITE", "EXECUTE")
        for k in list(ace.get("perms", {}).keys()):
            if k not in posix_ok:
                ace["perms"].pop(k, None)


def main():
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "str", "required": True},
            "username": {"type": "str", "default": None},
            "uid": {"type": "int", "default": None},
            "groupname": {"type": "str", "default": None},
            "gid": {"type": "int", "default": None},
            "dacl_nfs4": {
                "type": "list",
                "elements": "dict",
                "default": [],
                "options": {
                    "tag": {
                        "type": "str",
                        "choices": [
                            "owner@",
                            "group@",
                            "everyone@",
                            "USER",
                            "GROUP",
                        ],
                    },
                    "username": {"type": "str", "default": None},
                    "groupname": {"type": "str", "default": None},
                    "id": {"type": "int", "default": None},
                    "type": {
                        "type": "str",
                        "choices": ["ALLOW", "DENY"],
                    },
                    "perms": {
                        "type": "dict",
                        "default": {},
                        "options": {
                            "READ_DATA": {"type": "bool", "default": False},
                            "WRITE_DATA": {"type": "bool", "default": False},
                            "APPEND_DATA": {"type": "bool", "default": False},
                            "READ_NAMED_ATTRS": {"type": "bool", "default": False},
                            "WRITE_NAMED_ATTRS": {"type": "bool", "default": False},
                            "EXECUTE": {"type": "bool", "default": False},
                            "DELETE_CHILD": {"type": "bool", "default": False},
                            "READ_ATTRIBUTES": {"type": "bool", "default": False},
                            "WRITE_ATTRIBUTES": {"type": "bool", "default": False},
                            "DELETE": {"type": "bool", "default": False},
                            "READ_ACL": {"type": "bool", "default": False},
                            "WRITE_ACL": {"type": "bool", "default": False},
                            "WRITE_OWNER": {"type": "bool", "default": False},
                            "SYNCHRONIZE": {"type": "bool", "default": False},
                            "BASIC": {
                                "type": "str",
                                "choices": [
                                    "FULL_CONTROL",
                                    "MODIFY",
                                    "READ",
                                    "TRAVERSE",
                                ],
                            },
                        },
                    },
                    "flags": {
                        "type": "dict",
                        "default": {},
                        "options": {
                            "FILE_INHERIT": {"type": "bool", "default": False},
                            "DIRECTORY_INHERIT": {"type": "bool", "default": False},
                            "NO_PROPAGATE_INHERIT": {"type": "bool", "default": False},
                            "INHERIT_ONLY": {"type": "bool", "default": False},
                            "INHERITED": {"type": "bool", "default": False},
                            "BASIC": {
                                "type": "str",
                                "choices": ["INHERIT", "NOINHERIT"],
                            },
                        },
                    },
                },
            },
            "dacl_posix": {
                "type": "list",
                "elements": "dict",
                "default": [],
                "options": {
                    "default": {"type": "bool", "default": False},
                    "tag": {
                        "type": "str",
                        "choices": [
                            "USER_OBJ",
                            "GROUP_OBJ",
                            "USER",
                            "GROUP",
                            "OTHER",
                            "MASK",
                        ],
                    },
                    "username": {"type": "str", "default": None},
                    "groupname": {"type": "str", "default": None},
                    "id": {"type": "int", "default": -1},
                    "perms": {
                        "type": "dict",
                        "default": {},
                        "options": {
                            "READ": {"type": "bool", "default": False},
                            "WRITE": {"type": "bool", "default": False},
                            "EXECUTE": {"type": "bool", "default": False},
                        },
                    },
                },
            },
            "nfs41_flags": {
                "type": "dict",
                "default": {},
                "options": {
                    "autoinherit": {"type": "bool", "default": False},
                    "protected": {"type": "bool", "default": False},
                    "defaulted": {"type": "bool", "default": False},
                },
            },
            "acltype": {
                "type": "str",
                "choices": ["NFS4", "POSIX1E", "DISABLED"],
                "default": None,
            },
            "options": {
                "type": "dict",
                "default": {},
                "options": {
                    "stripacl": {"type": "bool", "default": False},
                    "recursive": {"type": "bool", "default": False},
                    "traverse": {"type": "bool", "default": False},
                    "canonicalize": {"type": "bool", "default": True},
                    "validate_effective_acl": {"type": "bool", "default": True},
                },
            },
        },
        mutually_exclusive=[
            ["username", "uid"],
            ["groupname", "gid"],
            ["dacl_nfs4", "dacl_posix"],
        ],
        supports_check_mode=True,
    )

    result = dict(changed=False, msg="")
    mw: Midclt = MW.client()
    path = module.params["path"]
    acl_type = module.params["acltype"]

    #
    # 1) Convert top-level username -> uid (if needed)
    #
    if module.params["username"]:
        try:
            user_info = mw.call(
                "user.get_user_obj", {"username": module.params["username"]}
            )
        except Exception as e:
            module.fail_json(
                msg=f"Failed to look up user '{module.params['username']}': {str(e)}"
            )
        if not user_info or "pw_uid" not in user_info:
            module.fail_json(msg=f"Invalid data from user lookup: {user_info}")
        module.params["uid"] = user_info["pw_uid"]

    #
    # 2) Convert top-level groupname -> gid (if needed)
    #
    if module.params["groupname"]:
        try:
            group_info = mw.call(
                "group.get_group_obj", {"groupname": module.params["groupname"]}
            )
        except Exception as e:
            module.fail_json(
                msg=f"Failed to look up group '{module.params['groupname']}': {str(e)}"
            )
        if not group_info or "gr_gid" not in group_info:
            module.fail_json(msg=f"Invalid data from group lookup: {group_info}")
        module.params["gid"] = group_info["gr_gid"]

    #
    # 3) Check NFS4 vs. POSIX1E
    #
    if module.params["dacl_nfs4"] and acl_type != "NFS4":
        module.fail_json(msg="dacl_nfs4 requires acltype=NFS4.")
    if module.params["dacl_posix"] and acl_type != "POSIX1E":
        module.fail_json(msg="dacl_posix requires acltype=POSIX1E.")

    if acl_type == "NFS4":
        # Convert name-based entries -> numeric IDs
        try:
            convert_acl_entry_names(mw, module.params["dacl_nfs4"], is_nfs4=True)
        except ValueError as ve:
            module.fail_json(msg=f"Error converting NFS4 ACL entries: {ve}")

    if acl_type == "POSIX1E":
        try:
            convert_acl_entry_names(mw, module.params["dacl_posix"], is_nfs4=False)
        except ValueError as ve:
            module.fail_json(msg=f"Error converting POSIX ACL entries: {ve}")

    #
    # 4) Retrieve existing ACL
    #
    try:
        existing_acl = mw.call("filesystem.getacl", path)
    except Exception as e:
        module.fail_json(msg=f"Error retrieving ACL for {path}: {e}")

    changed_fields = []
    fields_to_compare = [
        ("uid", "uid"),
        ("gid", "gid"),
        ("acltype", "acltype"),
    ]

    updated_acl = {"path": path, "options": module.params["options"] or None}

    if acl_type == "NFS4":
        fields_to_compare.append(("acl", "dacl_nfs4"))
        updated_acl["nfs41_flags"] = module.params.get("nfs41_flags", {})
    elif acl_type == "POSIX1E":
        fields_to_compare.append(("acl", "dacl_posix"))

    #
    # 5) Build updated ACL payload
    #
    for existing_field, updated_field in fields_to_compare:
        if existing_field == "acl":
            updated_acl["dacl"] = strip_default_values(
                module.params.get(updated_field),
                module.argument_spec.get(updated_field),
            )

        else:
            updated_acl[updated_field] = module.params.get(updated_field)

    # Cleanup final data so it exactly matches what TrueNAS expects
    if acl_type == "NFS4" and "dacl" in updated_acl:
        cleanup_nfs4_aces_for_setacl(updated_acl["dacl"])
    elif acl_type == "POSIX1E" and "dacl" in updated_acl:
        cleanup_posix_aces_for_setacl(updated_acl["dacl"])

    # raise ValueError(f"updated_acl: {updated_acl}")
    #
    # 6) Compare to existing
    #
    for existing_field, updated_field in fields_to_compare:
        if existing_field not in existing_acl and updated_field in module.params:
            changed_fields.append((existing_field, updated_field))
            continue
        if existing_field in existing_acl and updated_field not in module.params:
            changed_fields.append((existing_field, updated_field))
            continue
        if existing_field not in existing_acl and updated_field not in module.params:
            continue

        if existing_field == "acl":
            # If it's the ACL, we're comparing existing_acl["acl"] vs updated_acl["dacl"]
            param_value = (
                updated_acl["dacl"]
                if existing_field == "acl"
                else module.params.get(updated_field)
            )
            striped_param_value = param_value
        else:
            param_value = module.params.get(updated_field)
            striped_param_value = strip_default_values(
                param_value,
                module.argument_spec.get(updated_field, {}),
            )

        changed = has_object_changed(
            existing_acl.get(existing_field), striped_param_value
        )

        if changed:
            changed_fields.append((existing_field, updated_field))

    if not changed_fields:
        module.exit_json(changed=False, msg="No changes detected.")
        return

    if module.check_mode:
        module.exit_json(changed=True, msg=f"Would update {path} with: {updated_acl}")

    #
    # 7) Apply the ACL update
    #
    try:
        mw.job("filesystem.setacl", updated_acl)
    except Exception as e:
        module.fail_json(msg=f"Error setting ACL on {path} with {updated_acl}: {e}")

    module.exit_json(
        changed=True,
        msg=f"Updated resource {path}. Changed fields: {[uf for (_, uf) in changed_fields]}",
    )


if __name__ == "__main__":
    main()
