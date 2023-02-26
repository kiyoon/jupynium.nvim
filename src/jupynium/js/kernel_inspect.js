// NOTE: use driver.execute_async_script() to run this script
//
// Get variable information from the kernel
// Inspired by lkhphuc/jupyter-kernel.nvim
// arguments: a line of code, cursor position

// Make callback synchronous
// https://stackoverflow.com/questions/46021802/python-selenium-execute-script-vs-execute-async

var return_callback = arguments[arguments.length - 1] // this is used for returning the result.
function inspectCallback(result) {
  return_callback(result.content)
}

Jupyter.notebook.kernel.inspect(arguments[0], arguments[1], inspectCallback)

// Only wait for 5 seconds
setTimeout(function () {
  return_callback(null)
}, 5000)
