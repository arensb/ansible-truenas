# certificate action plugin.
#
# Several options to the 'certificate' module involve reading a file
# on the control host, and transferring it to the client host. So we
# use an action module to check the arguments, read the files, and
# pass them on to the 'certificate' module.

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ..modules.certificate import \
    argument_spec, required_if, mutually_exclusive

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        # This will raise an exception if the arguments are invalid.
        validation_result, new_module_args = self.validate_argument_spec(
            argument_spec=argument_spec,
            required_if=required_if,
            mutually_exclusive=mutually_exclusive,
        )

        subtask = self._task.copy()

        if 'src' in subtask.args and subtask.args['src'] is not None:
            # We were given a 'src' argument. Replace it with a
            # 'certificate' argument.
            try:
                with open(subtask.args['src'], 'rt') as f:
                    certificate = f.read()
            except Exception as e:
                raise AnsibleActionFail(f"Error opening 'src: {subtask.args['src']}': {e}")

            # Replace 'src' with 'certificate'.
            del subtask.args['src']
            subtask.args['certificate'] = certificate

        if 'private_keyfile' in subtask.args and subtask.args['private_keyfile'] is not None:
            # We were given a 'private_keyfile' argument. Replace it
            # with a 'private_key' argument.
            try:
                with open(subtask.args['private_keyfile'], 'rt') as f:
                    private_key = f.read()
            except Exception as e:
                raise AnsibleActionFail(f"Error opening 'src: {subtask.args['private_keyfile']}': {e}")

            # Replace 'private_keyfile' with 'private_key'.
            del subtask.args['private_keyfile']
            subtask.args['private_key'] = private_key

        # Now run the actual module.
        result = self._execute_module(module_name="certificate",
                                      module_args=subtask.args,
                                      task_vars=task_vars)
        return result
