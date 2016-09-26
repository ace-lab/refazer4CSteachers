
import pg_logger
import json
import pprint

pp = pprint.PrettyPrinter(depth=2)

def finalizer(output_list):
  # output_json = json.dumps(output_list)
  pp.pprint(output_list)

file = open('test/test-0.py', 'r')
script_str = file.read()

raw_input_json = ''
options_json = ''

# pg_logger.exec_script_str(script_str, raw_input_json, options_json, finalizer)
pg_logger.exec_script_str(script_str, finalizer)


