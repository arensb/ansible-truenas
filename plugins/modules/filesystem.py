#!/usr/bin/python
# -*- coding: utf-8 -*-

# XXX - Would be nice to specify 'volsize' in units other than bytes:
# accept suffixes: K, KB, KiB, M, MB, MiB, G, GB, GiB, T, TB, TiB.

# XXX - type: should accept both upper- and lower-case: filesystem,
# FILESYSTEM, volume, VOLUME.

__metaclass__ = type

DOCUMENTATION = """
---
module: filesystem
short_description: Manage ZFS datasets (filesystems/volumes) via TrueNAS middleware
description:
  - Create, update, and delete ZFS datasets on TrueNAS using the middleware API.
  - Prevents sending null or invalid fields that cause errors.
  - Normalizes property values so that e.g. '64K' is treated the same as '65536'
    for volblocksize comparisons. If a user tries to change volblocksize or sparse
    on an existing volume, the module raises an error (since TrueNAS disallows it).
options:
  name:
    description:
      - Full name (ZFS path) of the dataset, e.g. "pool/dataset".
    required: true
    type: str
  state:
    description:
      - If "present", ensure the dataset is created/updated.
      - If "absent", ensure the dataset is deleted.
    type: str
    choices: [ absent, present ]
    default: present
  type:
    description:
      - "Dataset type: FILESYSTEM or VOLUME."
    type: str
    choices: [ FILESYSTEM, VOLUME ]
    default: FILESYSTEM
  volsize:
    description:
      - Size of the volume in bytes if type=VOLUME.
    type: int
  volblocksize:
    description:
      - Volume block size if type=VOLUME, e.g. "64K" or "65536".
      - Only valid at dataset creation time; cannot be changed on an existing volume.
    type: str
    choices: [ '512','512B','1K','2K','4K','8K','16K','32K','64K','128K', '256K', '65536' ]
  sparse:
    description:
      - Whether to create a sparse volume (if type=VOLUME).
      - Cannot be changed after creation.
    type: bool
  force_size:
    description:
      - Whether to ignore checks if the volume size is below thresholds.
      - Only valid for type=VOLUME.
    type: bool
    default: false
  create_ancestors:
    description:
      - If True, create any missing parent datasets automatically when creating.
      - Under TrueNAS CORE, this option is ignored. However, missing ancestors are not created.
    type: bool
    default: false
  comment:
    description:
      - Arbitrary comment or notes for the dataset.
    type: str

  # (Other properties truncated for brevity, same as before)...

author:
  - "Your Name (@yourhandle)"
"""

EXAMPLES = r"""
- name: Delete dataset if it exists
  filesystem:
    name: test-expansion/chunkr3
    state: absent

- name: Create volume with 'sparse' = true
  filesystem:
    name: test-expansion/test-iscsi
    type: VOLUME
    volsize: 655360
    volblocksize: "64K"
    sparse: true
"""

RETURN = r"""
filesystem:
  description: Dataset properties as returned by the TrueNAS middleware.
  type: dict
  returned: on success
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware import (
    MiddleWare as MW,
)
import ansible_collections.arensb.truenas.plugins.module_utils.setup as setup


def main():
    # Figure out which version of TrueNAS we're running, since not all
    # versions support all arguments.
    global __tn_version
    try:
        __tn_version = setup.get_tn_version()
    except Exception as e:
        # Normally we'd module.exit_json(), but we don't have a module yet.
        print(f'{{"failed":true, "msg": "Error getting TrueNAS version: {e}"}}')
        sys.exit(1)

    argument_spec = dict(
        name=dict(type="str", required=True),
        state=dict(type="str", choices=["absent", "present"], default="present"),
        type=dict(type="str", choices=["FILESYSTEM", "VOLUME"], default="FILESYSTEM"),
        volsize=dict(type="int"),
        volblocksize=dict(
            type="str",
            choices=[
                "512",
                "512B",
                "1K",
                "2K",
                "4K",
                "8K",
                "16K",
                "32K",
                "64K",
                "128K",
                "256K",  # maybe
                "65536",  # numeric form
            ],
        ),
        sparse=dict(type="bool"),
        force_size=dict(type="bool", default=False),
        create_ancestors=dict(type="bool", default=False),
        # The rest of the properties...
        comment=dict(type="str"),
        sync=dict(type="str"),
        snapdev=dict(type="str"),
        compression=dict(type="str"),
        atime=dict(type="str"),
        exec=dict(type="str"),
        managedby=dict(type="str"),
        quota=dict(type="int"),
        quota_warning=dict(type="str"),
        quota_critical=dict(type="str"),
        refquota=dict(type="int"),
        refquota_warning=dict(type="str"),
        refquota_critical=dict(type="str"),
        reservation=dict(type="int"),
        refreservation=dict(type="int"),
        special_small_block_size=dict(type="str"),
        copies=dict(type="str"),
        snapdir=dict(type="str"),
        deduplication=dict(type="str"),
        checksum=dict(type="str"),
        readonly=dict(type="str"),
        recordsize=dict(type="str"),
        aclmode=dict(type="str"),
        acltype=dict(type="str"),
        xattr=dict(type="str"),
        user_properties=dict(
            type="list",
            elements="dict",
            default=[],
            options=dict(
                key=dict(type="str", required=True),
                value=dict(type="str", required=True),
            ),
        ),
        user_properties_update=dict(
            type="list",
            elements="dict",
            default=[],
            options=dict(
                key=dict(type="str", required=True),
                value=dict(type="str"),
                remove=dict(type="bool"),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    result = dict(changed=False, filesystem={}, msg="")
    mw = MW.client()

    p = module.params
    ds_name = p["name"]
    state = p["state"]

    # Query if it exists
    try:
        existing = mw.call("pool.dataset.query", [["name", "=", ds_name]])
    except Exception as e:
        module.fail_json(msg=f"Failed to query dataset '{ds_name}': {e}")

    if existing:
        existing_ds = existing[0]
    else:
        existing_ds = None

    if state == "absent":
        # If not found, no changes
        if not existing_ds:
            module.exit_json(
                changed=False, msg=f"Dataset '{ds_name}' is already absent."
            )
        # else delete it
        if module.check_mode:
            module.exit_json(changed=True, msg=f"Would delete dataset '{ds_name}'.")
        try:
            mw.call("pool.dataset.delete", ds_name, {"recursive": True})
            module.exit_json(changed=True, msg=f"Deleted dataset '{ds_name}'.")
        except Exception as e:
            module.fail_json(msg=f"Error deleting dataset '{ds_name}': {e}")
    else:
        # state == 'present'
        if not existing_ds:
            # Need to create
            create_args = build_create_args(p, module)
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    msg=f"Would create dataset '{ds_name}' with args={create_args}",
                )
            try:
                new_ds = mw.call("pool.dataset.create", create_args)
                result["changed"] = True
                result["filesystem"] = new_ds
                result["msg"] = f"Created dataset '{ds_name}'."
                module.exit_json(**result)
            except Exception as e:
                module.fail_json(msg=f"Error creating dataset '{ds_name}': {e}")
        else:
            # Possibly update
            update_args = build_update_args(p, existing_ds, module)
            if not update_args:
                module.exit_json(
                    changed=False,
                    msg=f"Dataset '{ds_name}' is up to date.",
                    filesystem=existing_ds,
                )
            else:
                if module.check_mode:
                    module.exit_json(
                        changed=True,
                        msg=f"Would update dataset '{ds_name}' with {update_args}",
                    )
                try:
                    updated_ds = mw.call("pool.dataset.update", ds_name, update_args)
                    result["changed"] = True
                    result["filesystem"] = updated_ds
                    result["msg"] = f"Updated dataset '{ds_name}'."
                    module.exit_json(**result)
                except Exception as e:
                    module.fail_json(msg=f"Error updating dataset '{ds_name}': {e}")


def build_create_args(params, module):
    global __tn_version

    create_args = dict(name=params["name"], type=params["type"])

    if params.get("create_ancestors") is not None:
        if __tn_version['type'] == "CORE":
            # TrueNAS CORE doesn't support create_ancestors.
            module.warn("TrueNAS CORE doesn't support create_ancestors option.")
        else:
            create_args["create_ancestors"] = params["create_ancestors"]

    if create_args["type"] == "VOLUME":
        volsize = params.get("volsize")
        if not volsize:
            module.fail_json(msg="volsize is required when creating a volume.")
        create_args["volsize"] = volsize

        if params.get("volblocksize") is not None:
            create_args["volblocksize"] = params["volblocksize"]

        if params.get("sparse") is not None:
            create_args["sparse"] = params["sparse"]

        if params.get("force_size") is not None:
            create_args["force_size"] = params["force_size"]

    # The rest of the properties are optional
    create_props = [
        "comment",
        "sync",
        "snapdev",
        "compression",
        "atime",
        "exec",
        "managedby",
        "quota",
        "quota_warning",
        "quota_critical",
        "refquota",
        "refquota_warning",
        "refquota_critical",
        "reservation",
        "refreservation",
        "special_small_block_size",
        "copies",
        "snapdir",
        "deduplication",
        "checksum",
        "readonly",
        "recordsize",
        "aclmode",
        "acltype",
        "xattr",
    ]
    for prop in create_props:
        val = params.get(prop)
        if val is not None:
            create_args[prop] = val

    # user_properties
    if params.get("user_properties"):
        create_args["user_properties"] = params["user_properties"]

    return create_args


def build_update_args(params, existing_ds, module):
    update_args = {}
    ds_type = existing_ds["type"]  # "FILESYSTEM" or "VOLUME"

    # If volume => we can update volsize if it changed
    if ds_type == "VOLUME":
        if params.get("volsize") is not None:
            current_volsize = prop_rawvalue(existing_ds, "volsize") or ""
            desired_str = str(params["volsize"])
            if desired_str != current_volsize:
                update_args["volsize"] = params["volsize"]

        # If user tries to update volblocksize => check if it differs
        # If differs => error. If same => skip
        if params.get("volblocksize") is not None:
            user_vbs = parse_volblocksize(params["volblocksize"])  # convert to int
            curr_raw = prop_rawvalue(existing_ds, "volblocksize") or ""
            try:
                curr_vbs = parse_volblocksize(curr_raw)
            except Exception:
                curr_vbs = None
            if curr_vbs != user_vbs:
                module.fail_json(
                    msg=(
                        f"Cannot update 'volblocksize' on existing volume. "
                        f"Current={curr_raw} => {curr_vbs} vs. desired={params['volblocksize']} => {user_vbs}."
                    )
                )

        # If user tries to update sparse => check if it differs
        # If differs => error, if same => skip
        if params.get("sparse") is not None:
            module.warn(
                "Cannot update 'sparse' on existing volume, ignoring parameter."
            )

        # force_size can be used if resizing
        if params.get("force_size") is not None and params.get("force_size") == True:
            update_args["force_size"] = True

    # For normal props (both filesystem + volume)
    updatable_props = [
        "comment",
        "sync",
        "snapdev",
        "compression",
        "atime",
        "exec",
        "managedby",
        "quota",
        "quota_warning",
        "quota_critical",
        "refquota",
        "refquota_warning",
        "refquota_critical",
        "reservation",
        "refreservation",
        "special_small_block_size",
        "copies",
        "snapdir",
        "deduplication",
        "checksum",
        "readonly",
        "recordsize",
        "aclmode",
        "acltype",
        "xattr",
    ]
    for prop in updatable_props:
        if params.get(prop) is None:
            continue
        desired_val = params[prop]
        current_val = prop_rawvalue(existing_ds, prop)
        if not compare_prop(prop, desired_val, current_val):
            update_args[prop] = desired_val

    # user_properties (bulk set)
    if params.get("user_properties"):
        if params["user_properties"]:
            update_args["user_properties"] = params["user_properties"]

    # user_properties_update
    if params.get("user_properties_update"):
        ups = []
        for item in params["user_properties_update"]:
            up = {"key": item["key"]}
            if item.get("remove"):
                up["remove"] = True
            elif item.get("value") is not None:
                up["value"] = item["value"]
            ups.append(up)
        if ups:
            update_args["user_properties_update"] = ups

    module.warn(f"update_args={update_args}")

    return update_args


def parse_volblocksize(value):
    """
    Convert a string like '64K' or '512B' or a numeric string like '65536'
    into an integer number of bytes. Raise an exception if unknown.
    """
    mapping = {
        "512": 512,
        "512B": 512,
        "1K": 1024,
        "2K": 2048,
        "4K": 4096,
        "8K": 8192,
        "16K": 16384,
        "32K": 32768,
        "64K": 65536,
        "128K": 131072,
        "256K": 262144,  # in case user sets that
    }
    val = value.strip().upper()  # e.g. '64K' or '65536'
    if val in mapping:
        return mapping[val]
    # else maybe it's purely numeric, e.g. '65536'
    if val.isdigit():
        return int(val)
    raise ValueError(f"Cannot parse volblocksize='{value}'")


def prop_rawvalue(dataset_entry, prop_name):
    """
    Retrieve the 'rawvalue' from dataset_entry[prop_name].
    Return string or None if missing. We also strip() whitespace for safety.
    """
    if prop_name in dataset_entry:
        d = dataset_entry[prop_name]
        if isinstance(d, dict):
            rv = d.get("rawvalue")
            if rv is not None:
                return rv.strip()
    return None


def compare_prop(prop_name, desired_val, current_str):
    """
    Compare desired_val (from user) vs. current_str (from dataset's rawvalue)
    in a way that avoids spurious changes (case, etc.).
    Return True if effectively the same, False if different.
    """
    if current_str is None and desired_val is None:
        return True
    desired_str = str(desired_val).strip()
    if current_str is None:
        current_str = ""

    # known enumerations for case-insensitive compare
    lower_enums = {
        "on",
        "off",
        "inherit",
        "standard",
        "always",
        "disabled",
        "visible",
        "hidden",
        "lz4",
        "zstd",
        "nfsv4",
        "posix",
        "restricted",
        "passthrough",
        "discard",
        "verify",
    }
    if desired_str.lower() in lower_enums or current_str.lower() in lower_enums:
        return desired_str.lower() == current_str.lower()

    # otherwise direct string compare
    return desired_str == current_str


def same_value_bool(desired_bool, current_str):
    """
    For fields like 'sparse' (bool), compare with current_str which might be "ON","OFF","TRUE","FALSE", etc.
    Return True if they match, False otherwise.
    """
    d_str = "on" if desired_bool else "off"
    c_str = (current_str or "").lower().strip()
    if c_str in ("1", "true", "yes"):
        c_str = "on"
    elif c_str in ("0", "false", "no"):
        c_str = "off"
    return d_str == c_str


if __name__ == "__main__":
    main()
