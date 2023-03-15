# Ansible Collection - arensb.truenas

Control a TrueNAS box using its API.

## Supported versions of Ansible
- Tested with 2.10.8

## Included content

This collection consists primarily of a set of Ansible modules to
configure a TrueNAS machine, using the
[TrueNAS API](https://www.truenas.com/docs/api/websocket.html)
to control the Middleware Daemon.

There are several ways to talk to the Middleware, but at present this
collection only supports running `midclt` commands on the box. So you
will need root access there, just as for any other Ansible client. In
the future, it may support RESTful control.

### Modules
Name                          | Description
----------------------------- | ------------------
`arensb.truenas.service`     | Manage services
`arensb.truenas.group`       | Manage Unix groups
`arensb.truenas.hostname`    | Set the hostname
`arensb.truenas.sharing_nfs` | Manage NFS exports
`arensb.truenas.user`        | Manage users

## Installing this collection

At some point, this will be available through Ansible Galaxy. Until then,
you can clone this repository someplace where Ansible will find it.

## Examples

    - name: Example tasks
      collections:
        - arensb.truenas
      hosts: truenas-box
      become: yes
      tasks:
        - name: Set the hostname
          hostname:
            name: new-hostname
        - name: Turn on sshd
          service:
            name: sshd

Note that since several of the module names are the same as builtin
ones, you may want to use the full name to avoid confusion:

    - hosts: truenas-box
      become: yes
      tasks:
        - arensb.truenas.hostname:
            name: new-hostname

The individual modules also have documentation strings, and should work with
`ansible-doc`, e.g.:

    ansible-doc -t module arensb.truenas.user

## Contributing to this collection
The best way to contribute a patch or feature is to create a pull request.

The `plugins/modules/template` file provides a starting point for new modules.

## Authors and Contributors

- Andrew Arensburger ([@arensb](https://mastodon.social/@arensb))
