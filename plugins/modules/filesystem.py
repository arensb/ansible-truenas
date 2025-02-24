#!/usr/bin/python
# -*- coding: utf-8 -*-

__metaclass__ = type

DOCUMENTATION = """
---
module: filesystem
short_description: Manage ZFS datasets (filesystems/volumes) via TrueNAS middleware
description:
  - Create, update, and delete ZFS datasets on TrueNAS using the middleware API.
  - Prevents sending null or invalid fields that cause errors.
  - Normalizes property values to avoid marking the dataset as "changed"
    when the system returns a different capitalization or format.
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
      - Dataset type: FILESYSTEM or VOLUME.
    type: str
    choices: [ FILESYSTEM, VOLUME ]
    default: FILESYSTEM

  volsize:
    description:
      - Size of the volume in bytes if type=VOLUME.
    type: int

  volblocksize:
    description:
      - Volume block size if type=VOLUME.
    type: str
    choices: [ '512','512B','1K','2K','4K','8K','16K','32K','64K','128K' ]

  sparse:
    description:
      - Whether to create a sparse volume (if type=VOLUME).
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
    type: bool
    default: false

  comments:
    description:
      - Comment or "INHERIT".
      - Omit if you do not want a comment (null not allowed by some TrueNAS versions).
    type: str

  sync:
    description:
      - "STANDARD", "ALWAYS", "DISABLED", or "INHERIT".
    type: str

  snapdev:
    description:
      - "HIDDEN", "VISIBLE", or "INHERIT".
    type: str

  compression:
    description:
      - Compression setting ("OFF", "LZ4", "ZSTD", etc.) or "INHERIT".
    type: str

  atime:
    description:
      - "ON", "OFF", or "INHERIT".
    type: str

  exec:
    description:
      - "ON", "OFF", or "INHERIT".
    type: str

  managedby:
    description:
      - Arbitrary string or "INHERIT".
    type: str

  quota:
    description:
      - Integer or None, specifying a dataset quota.
    type: int

  quota_warning:
    description:
      - Integer or "INHERIT".
    type: str

  quota_critical:
    description:
      - Integer or "INHERIT".
    type: str

  refquota:
    description:
      - Integer or None, specifying a "referenced" quota for the dataset only.
    type: int

  refquota_warning:
    description:
      - Integer or "INHERIT".
    type: str

  refquota_critical:
    description:
      - Integer or "INHERIT".
    type: str

  reservation:
    description:
      - Bytes reserved for this dataset.
    type: int

  refreservation:
    description:
      - Bytes reserved for this dataset (not counting descendants).
    type: int

  special_small_block_size:
    description:
      - Integer or "INHERIT".
    type: str

  copies:
    description:
      - Integer or "INHERIT".
    type: str

  snapdir:
    description:
      - "VISIBLE", "HIDDEN", or "INHERIT".
    type: str

  deduplication:
    description:
      - "ON", "VERIFY", "OFF", or "INHERIT".
    type: str

  checksum:
    description:
      - "ON", "OFF", "FLETCHER2", etc., or "INHERIT".
    type: str

  readonly:
    description:
      - "ON", "OFF", or "INHERIT".
    type: str

  recordsize:
    description:
      - e.g. "128K" or "INHERIT".
    type: str

  aclmode:
    description:
      - "PASSTHROUGH", "RESTRICTED", "DISCARD", or "INHERIT".
    type: str

  acltype:
    description:
      - "OFF", "NFSV4", "POSIX", or "INHERIT".
    type: str

  xattr:
    description:
      - "ON", "SA", or "INHERIT".
      - Omit if "Field was not expected" error occurs.
    type: str

  user_properties:
    description:
      - Array of user properties to set on the dataset (bulk set).
    type: list
    elements: dict
    default: []
    suboptions:
      key:
        description: The property name.
        type: str
        required: true
      value:
        description: The property value.
        type: str
        required: true

  user_properties_update:
    description:
      - List of user properties to selectively add/modify/remove.
      - If remove=true, the property is removed.
      - If value is set, the property is added or replaced.
    type: list
    elements: dict
    default: []
    suboptions:
      key:
        description: The property name.
        type: str
        required: true
      value:
        description: The property value (omit or null if removing).
        type: str
      remove:
        description: If true, remove the user property entirely.
        type: bool

author:
  - "Your Name (@yourhandle)"
"""

EXAMPLES = r"""
- name: Delete dataset if it exists
  filesystem:
    name: test-expansion/chunkr3
    state: absent

- name: Create dataset with specific ACL
  filesystem:
    name: test-expansion/chunkr3
    state: present
    acltype: NFSV4
    aclmode: RESTRICTED

# Running it twice in a row should not show "changed" if the
# dataset already matches these properties.
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


def main():
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
            ],
        ),
        sparse=dict(type="bool"),
        force_size=dict(type="bool", default=False),
        create_ancestors=dict(type="bool", default=False),
        comments=dict(type="str"),
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
            update_args = build_update_args(p, existing_ds)
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
    """
    Build the arguments to pass to pool.dataset.create, ensuring
    we only include fields that are non-None and valid for the dataset type.
    """
    create_args = dict(name=params["name"], type=params["type"])

    if params.get("create_ancestors") is not None:
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

    # For FILESYSTEM, do NOT include force_size or other VOLUME fields
    # The rest of the props are optional for either type, so include if not None
    create_props = [
        "comments",
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


def build_update_args(params, existing_ds):
    """
    Build arguments for pool.dataset.update, comparing param values
    to existing rawvalue so we only update changed props.
    If a param is None, do not pass it at all.
    We also do case-insensitive comparison for certain fields so that
    if the system returns "ON" but the user sets "on", we do not incorrectly
    treat it as changed.
    """
    update_args = {}
    ds_type = existing_ds["type"]  # "FILESYSTEM" or "VOLUME"

    if ds_type == "VOLUME":
        if params.get("volsize") is not None:
            current_volsize = prop_rawvalue(existing_ds, "volsize")
            desired_str = str(params["volsize"])
            if desired_str != current_volsize:
                update_args["volsize"] = params["volsize"]

        if params.get("sparse") is not None:
            current_sparse = prop_rawvalue(existing_ds, "sparse")
            if not same_value_bool(params["sparse"], current_sparse):
                update_args["sparse"] = params["sparse"]

        if params.get("force_size") is not None:
            # Always set force_size if user wants it
            update_args["force_size"] = params["force_size"]

    # Updatable props for either type
    updatable_props = [
        "comments",
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
            if "remove" in item and item["remove"] is True:
                up["remove"] = True
            elif "value" in item and item["value"] is not None:
                up["value"] = item["value"]
            ups.append(up)
        if ups:
            update_args["user_properties_update"] = ups

    return update_args


def prop_rawvalue(dataset_entry, prop_name):
    """
    Retrieve the 'rawvalue' from the dataset_entry[prop_name].
    Return string or None if missing. We also strip() whitespace for safety.
    """
    p = dataset_entry.get(prop_name, {})
    rv = p.get("rawvalue", None)
    if rv is None:
        return None
    return str(rv).strip()


def compare_prop(prop_name, desired_val, current_str):
    """
    Compare desired_val (from user) vs. current_str (from rawvalue)
    in a way that avoids spurious changes. We do some normalization:
      - Strip leading/trailing whitespace
      - For certain enumerations, compare ignoring case
      - For booleans, compare "on"/"off"/"true"/"false"/"1"/"0"
    Return True if they are effectively the same, False if different.
    """

    if current_str is None and desired_val is None:
        return True  # both None

    # Convert desired_val to string, strip
    desired_str = str(desired_val).strip()

    # If this property is known to be an ON/OFF style boolean or an enumerated string:
    # We'll define some known sets:
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
    # We also know uppercase variants (like NFSV4) appear, so let's do case-insensitive
    # for "on"/"off"/"inherit"/"nfsv4"/"posix"/"restricted"/"passthrough"/"discard", etc.

    # We'll do a simple approach: if both desired_str and current_str
    # are in that set (case-insensitive), compare in lower-case:
    if desired_str.lower() in lower_enums or current_str.lower() in lower_enums:
        return desired_str.lower() == current_str.lower()

    # Possibly check for booleans "true"/"false"/"1"/"0"
    # if you need that, e.g. for 'sparse' or 'exec'.
    # We have a helper for that below if needed:
    # But let's skip unless we know it's boolean.

    # Otherwise, direct string compare
    return desired_str == current_str


def same_value_bool(desired_bool, current_str):
    """
    A helper specifically for a bool field like 'sparse', where
    desired_bool is a Python bool and current_str is the rawvalue
    that might be "true", "false", "on", "off", "1", "0".
    """
    # Convert desired_bool -> "true"/"false"
    d_str = "true" if desired_bool else "false"
    # Convert current_str to lower
    c_str = (current_str or "").lower().strip()
    if c_str in ("on", "1"):
        c_str = "true"
    elif c_str in ("off", "0"):
        c_str = "false"
    # Now compare
    return d_str == c_str


if __name__ == "__main__":
    main()
