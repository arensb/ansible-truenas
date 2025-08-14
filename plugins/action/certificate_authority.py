# certificate_authority action plugin.
#
# The 'src' option to 'certificate_authority' involves a file on the
# control host being converted to a string on the client. That's not
# something that the 'certificate_authority' module can do, since it
# runs entirely on the remote client. So we need this action plugin to
# act as a wrapper.

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ..modules.certificate_authority import \
    argument_spec, required_if, mutually_exclusive

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)
        result['action_msg'] = "Hello from action module.\n"	# XXX - debugging

        # This will raise an exception if the arguments are invalid.
        validation_result, new_module_args = self.validate_argument_spec(
            argument_spec=argument_spec,
            required_if=required_if,
            mutually_exclusive=mutually_exclusive,
        )

        subtask = self._task.copy()

        if 'src' in subtask.args and subtask.args['src'] is not None:
            # We were given a 'src' argument. Replace it with a
            # 'content' argument.
            try:
                with open(subtask.args['src'], 'rt') as f:
                    content = f.read()
            except Exception as e:
                raise AnsibleActionFail(f"Error opening 'src: {subtask.args['src']}': {e}")

            # Replace 'src' with 'content'.
            del subtask.args['src']
            subtask.args['content'] = content

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
        result = self._execute_module(module_name="certificate_authority",
                                      module_args=subtask.args,
                                      task_vars=task_vars)
        result['action_args'] = self._task.args

        return result

