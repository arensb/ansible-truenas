#!/usr/bin/python
# -*- coding: utf-8 -*-
__metaclass__ = type

# Manage ups service configuration

DOCUMENTATION = '''
---
module: ups
short_description: Manage ups service configuration
description: Manage ups service configuration
author:
  - Wojciech Matusiak (@wmatusiak)
version_added: "1.15.0"
attributes:
  check_mode:
    description: Can run in check_mode and return changed status predication without modifying target
    support: full
  diff_mode:
    description: Will return details onn what has changed (or possibly needs changing in check_mode), when in diff mode
    support: full
  platform:
    description: Target OS/families that can by opereted against
    support: full
    platforms: TrueNAS
options:
  identifier:
    description: Describe the UPS device. It can contain alphanumeric, period, comma, hyphen, and underscore characters.
    type: str
    default: ups
  mode:
    description:
      - Choose Master if the UPS is plugged directly into the system serial port.
      - The UPS will remain the last item to shut down.
      - Choose Slave to have this system shut down before Master. See the Network UPS Tools Overview.
    type: str
    choices: [ master, slave ]
    default: master
  remote_host:
    description:
      - IP address of the remote system with UPS Mode set as Master.
      - Enter a valid IP address in the format 192.168.0.1
      - Required if mode is slave
    type: str
  remote_port:
    description:
      - When the UPS Mode is set to slave. Enter the open network port number of the UPS Master system.
      - The default port is 3493.
      - Used if mode is slave
    type: int
    default: 3493
  driver:
    description:
      - See the Network UPS Tools compatibility list for a list of supported UPS devices.
      - Required if mode is master
    type: str
  port:
    description:
      - Serial or USB port connected to the UPS. To automatically detect and manage the USB port settings, select auto.
      - When an SNMP driver is selected, enter the IP address or hostname of the SNMP UPS device.
    type: str
    default: auto
  monitor_user:
    description: Enter a user to associate with this service. Keeping the default is recommended.
    type: str
    default: upsmon
  monitor_pass:
    description: Change the default password to improve system security. The new password cannot contain a space or #.
    type: str
    required: true
  extra_users:
    description: Enter accounts that have administrative access. See upsd.users(5) for examples.
    type: list
    elements: dict
    suboptions:
      name:
        description: Name of user
        type: str
        required: true
      password:
        description: Set the password forthis user
        type: str
        required: true
      actions:
        description:
          - Allow the user to do certain things with upsd.
          - "Valid actions are:"
          - set - change the value of certain variables in the UPS
          - fsd - set the forced shutdown flag in the UPS. This is equivalent to an "on battery + low battery" situation for the purposes of monitoring.
        type: list
        elements: str
        choices: [ set, fsd ]
      instcmds:
        description:
          - Let a user initiate specific instant commands.
          - Use "ALL" to grant all commands automatically.
          - For the full list of what your UPS supports, use upscmd -l.
          - The cmdvartab file supplied with the NUT distribution contains a list of most of the generally known command names
        type: list
        elements: str
      upsmon:
        description:
          - Add the necessary actions for an upsmon process, and can be viewed as a role of a particular client instance to work with this data server instance.
          - This is either set to primary (may request FSD) or secondary (follows critical situations to shut down when needed).
          - Do not attempt to assign actions to upsmon by hand, as you may miss something important.
          - This method of designating a "upsmon user" was created so internal capabilities could be changed later on without breaking existing installations
          - (potentially using actions that are not exposed for direct assignment).
        type: str
        choices: [ primary, secondary ]
  remote_monitor:
    description: Set for the default configuration to listen on all interfaces using the known values of monitor_user and monitor_pas.
    type: bool
    default: false
  shutdown_mode:
    description:
      - Choose when the UPS initiates shutdown.
      - BATT - Shutdown when ups goes on battery
      - LOWBATT - Shutdown when ups reaches low battery
    type: str
    choices: [ BATT, LOWBATT ]
    default: LOWBATT
  shutdown_timer:
    description:
      - Enter a value in seconds for the the UPS to wait before initiating shutdown.
      - Shutdown will not occur if power is restored while the timer is counting down.
      - This value only applies when Shutdown mode is set to UPS goes on battery.
    type: int
    default: 30
  shutdown_cmd:
    description: Enter a command to shut down the system when either battery power is low or the shutdown timer ends.
    type: str
  send_email_status_update:
    description: Enable sending messages to the address defined in the email field.
    type: bool
    default: false
  email:
    description: Email addresses to receive status updates.
    type: list
    elements: str
  email_subject:
    description: Subject for status emails.
    type: str
    default: UPS report generated by %h
  poweroff_ups:
    description: Set for the UPS to power off after shutting down the system.
    type: bool
    default: false
  no_comm_warning_time:
    description:
      - Enter a number of seconds to wait before alerting that the service cannot reach any UPS.
      - Warnings continue until the situation is fixed.
    type: int
  host_sync:
    description: Upsmon will wait up to this many seconds in master mode for the slaves to disconnect during a shutdown situation.
    type: int
    default: 15
  aux_param_ups:
    description: Enter any extra options from UPS.CONF(5).
    type: dict
  aux_param_upsd:
    description: Enter any extra options from UPSD.CONF(5).
    type: dict
'''

EXAMPLES = '''
- name: Configure UPS
  arensb.truenas.ups:
    driver: "snmp-ups$Smart-UPS RT XL"
    port: 192.168.1.250
    monitor_pass: "some random password"
- name: Enable UPS service
  arensb.truenas.service:
    name: ups
    enabled: yes
    state: started
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.middleware import MiddleWare as MW

try:
    import yaml
except ImportError:
    HAS_YAML = False
    YAML_IMPORT_ERROR = traceback.format_exc()
else:
    HAS_YAML = True
    YAML_IMPORT_ERROR = None


def format_extra_users(extra_users):
    res = ""
    if extra_users is None:
        return res

    for user in extra_users:
        res += f"[{user['name']}]\n"
        res += f"\tpassword = {user['password']}\n"
        if user['actions'] is not None:
            for action in user['actions']:
                res += f"\tactions = {action}\n"

        if user['instcmds'] is not None:
            for instcmd in user['instcmds']:
                res += f"\tinstcmds = {instcmd}\n"

        if user['upsmon'] is not None:
            res += f"\tupsmon {user['upsmon']}\n"

        res += "\n"

    return res


def format_dict(dict, glue):
    res = ""
    if dict is None:
        return res

    for key in dict:
        res += f"{key}{glue}{dict[key]}\n"

    return res


def map_args_to_info(args):
    res = {}
    map = {
        'remote_host': 'remotehost',
        'remote_port': 'remoteport',
        'monitor_user': 'monuser',
        'monitor_pass': 'monpwd',
        'extra_users': 'extrausers',
        'remote_monitor': 'rmonitor',
        'shutdown_mode': 'shutdown',
        'shutdown_timer': 'shutdowntimer',
        'shutdown_cmd': 'shutdowncmd',
        'send_email_status_update': 'emailnotify',
        'email': 'toemail',
        'email_subject': 'subject',
        'poweroff_ups': 'powerdown',
        'no_comm_warning_time': 'nocommwarntime',
        'host_sync': 'hostsync',
        'aux_param_ups': 'options',
        'aux_param_upsd': 'optionsupsd'
    }
    for key in args:
        if key in map:
            if key == 'extra_users':
                res[map[key]] = format_extra_users(args[key])
            elif key == 'aux_param_ups':
                res[map[key]] = format_dict(args[key], " = ")
            elif key == 'aux_param_upsd':
                res[map[key]] = format_dict(args[key], " ")
            else:
                res[map[key]] = args[key]
        else:
            res[key] = args[key]

    return res


def main():
    module = AnsibleModule(
        argument_spec=dict(
            identifier=dict(type='str', default='ups'),
            mode=dict(type='str', default='master', choices=['master', 'slave']),
            remote_host=dict(type='str'),
            remote_port=dict(type='int', default=3493),
            driver=dict(type='str'),
            port=dict(type='str', default='auto'),
            monitor_user=dict(type='str', default='upsmon'),
            monitor_pass=dict(type='str', required=True, no_log=True),
            extra_users=dict(type='list', elements='dict', options=dict(
                name=dict(type='str', required=True),
                password=dict(type='str', required=True, no_log=True),
                actions=dict(type='list', elements='str', choices=['set', 'fsd']),
                instcmds=dict(type='list', elements='str'),
                upsmon=dict(type='str', choices=['primary', 'secondary'])
            )),
            remote_monitor=dict(type='bool', default=False),
            shutdown_mode=dict(type='str', default='LOWBATT', choices=['BATT', 'LOWBATT']),
            shutdown_timer=dict(type='int', default=30),
            shutdown_cmd=dict(type='str'),
            send_email_status_update=dict(type='bool', default=False),
            email=dict(type='list', elements='str'),
            email_subject=dict(type='str', default='UPS report generated by %h'),
            poweroff_ups=dict(type='bool', default=False),
            no_comm_warning_time=dict(type='int'),
            host_sync=dict(type='int', default=15),
            aux_param_ups=dict(type='dict'),
            aux_param_upsd=dict(type='dict'),
        ),
        supports_check_mode=True,
        required_if=[
            ('mode', 'slave', ['remote_host']),
            ('mode', 'master', ['driver'])
        ],
        mutually_exclusive=[
            ('driver', 'remote_host'),
            ('driver', 'remote_port')
        ]
    )

    result = dict(changed=False, msg='')
    mw = MW.client()
    p = module.params

    # Get ups configuration
    try:
        ups_info = mw.call("ups.config")
    except Exception as e:
        module.fail_json(msg=f"Error requesting ups configuration: {e}")

    # Make list of differences between what is and what should be.
    arg = {}

    if ups_info['identifier'] != p['identifier']:
        arg['identifier'] = p['identifier']

    p['mode'] = p['mode'].upper()
    if ups_info['mode'] != p['mode']:
        arg['mode'] = p['mode']

    if p['mode'] == 'MASTER':
        if ups_info['driver'] != p['driver']:
            arg['driver'] = p['driver']
            arg['remotehost'] = ''
            arg['remoteport'] = 3493
    else:
        arg['driver'] = ''
        if ups_info['remotehost'] != p['remote_host']:
            arg['remotehost'] = p['remote_host']

        if ups_info['remoteport'] != p['remote_port']:
            arg['remoteport'] = p['remote_port']

    if ups_info['port'] != p['port']:
        arg['port'] = p['port']

    if ups_info['monuser'] != p['monitor_user']:
        arg['monuser'] = p['monitor_user']

    if ups_info['monpwd'] != p['monitor_pass']:
        arg['monpwd'] = p['monitor_pass']

    extra_users = format_extra_users(p['extra_users'])
    if ups_info['extrausers'] != extra_users:
        arg['extrausers'] = extra_users

    if ups_info['rmonitor'] != p['remote_monitor']:
        arg['rmonitor'] = p['remote_monitor']

    if ups_info['shutdown'] != p['shutdown_mode']:
        arg['shutdown'] = p['shutdown_mode']

    if ups_info['shutdowntimer'] != p['shutdown_timer']:
        arg['shutdowntimer'] = p['shutdown_timer']

    if ups_info['shutdowncmd'] != p['shutdown_cmd']:
        arg['shutdowncmd'] = p['shutdown_cmd']

    if ups_info['emailnotify'] != p['send_email_status_update']:
        arg['emailnotify'] = p['send_email_status_update']

    ups_info_email = set()
    if ups_info['toemail'] is not None:
        ups_info_email = set(ups_info['toemail'])

    p_email = set()
    if p['email'] is not None:
        p_email = set(p['email'])

    if len(ups_info_email ^ p_email) > 0:
        arg['toemail'] = p['email']
        if arg['toemail'] is None:
            arg['toemail'] = []

    if ups_info['subject'] != p['email_subject']:
        arg['subject'] = p['email_subject']

    if ups_info['powerdown'] != p['poweroff_ups']:
        arg['powerdown'] = p['poweroff_ups']

    if ups_info['nocommwarntime'] != p['no_comm_warning_time']:
        arg['nocommwarntime'] = p['no_comm_warning_time']

    if ups_info['hostsync'] != p['host_sync']:
        arg['hostsync'] = p['host_sync']

    aux_param_ups = format_dict(p['aux_param_ups'], " = ")
    if ups_info['options'] != aux_param_ups:
        arg['options'] = aux_param_ups

    aux_param_upsd = format_dict(p['aux_param_upsd'], " ")
    if ups_info['optionsupsd'] != aux_param_upsd:
        arg['optionsupsd'] = aux_param_upsd

    if len(arg) == 0:
        # No changes
        result['changed'] = False
    else:
        # Update resource.
        if module.check_mode:
            result['msg'] = f"Would have updated ups configuration: {arg}"
        else:
            try:
                mw.call("ups.update", arg)
            except Exception as e:
                module.fail_json(msg=f"Error updating ups configuration with {arg}: {e}")

        result['changed'] = True
        if module._diff:
            if not HAS_YAML:
                # If we dont have YAML library return diff send to ups.update
                result['diff'] = dict(prepered=arg)
                result['msg'] = 'Diff requested but missing YAML library. Diff contains data sent to the ups.update call.'
                result['msg'] += f"YAML library import error: {YAML_IMPORT_ERROR}"
            else:
                # Remove not chenging keys in ups_info
                for key in ['complete_identifier', 'description', 'id']:
                    ups_info.pop(key, None)

                # Prevent falls diff changes
                if p['remote_host'] is None:
                    p['remote_host'] = ''

                # Prevent falls diff changes
                if p['email'] is None:
                    p['email'] = []

                result['diff'] = dict(
                    before=yaml.safe_dump(ups_info),
                    after=yaml.safe_dump(map_args_to_info(p))
                )

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
