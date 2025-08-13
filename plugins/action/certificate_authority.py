from ansible.plugins.action import ActionBase

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        task_args=dict()
        task_vars['foo'] = "bar"
        # XXX - If necessary, open 'src' file and slurp it in.
        result = self._execute_module(module_name="certificate_authority",
                                      module_args=task_args,
                                      task_vars=task_vars)
        result['action_msg'] = "Hello, world!"

        return result

