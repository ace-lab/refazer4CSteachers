
import pg_logger
import json
import pprint

pp = pprint.PrettyPrinter(depth=2)

def finalizer(output_list):
  output_json = json.dumps(output_list)
  # print(output_json)

print('====== Before ======')
file = open('test/before.py', 'r')
before = file.read()
print(before)
print('')
before_traces = pg_logger.exec_script_str(before, finalizer).trace


print('======= After =======')
file = open('test/after.py', 'r')
after = file.read()
print(after)
print('')
after_traces = pg_logger.exec_script_str(after, finalizer).trace

traces = []
for i in range(len(before_traces)):
  before_trace = before_traces[i]
  after_trace = after_traces[i]

  before_locals = before_trace['stack_locals']
  after_locals = after_trace['stack_locals']
  trace = {
    'before_line': before_trace['line'],
    'after_line': after_trace['line']
  }

  for i in range(len(before_locals)):
    local = before_locals[i]
    if local[0] == 'accumulate':
      if local[1]['n']:
        trace['before_n'] = local[1]['n']

        after_local = after_locals[i]
        if after_local[0] == 'accumulate':
          if after_local[1]['n']:
            trace['after_n'] = after_local[1]['n']
        break

  print(trace)
  traces.append(trace)


