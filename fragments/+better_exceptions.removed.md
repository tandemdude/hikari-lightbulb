Removed `HookFailedException`. `ExecutionPipelineFailedException` now has two attributes containing the hooks that
failed, and the exception that caused them to fail. You may need to update your error handler to reflect this.
