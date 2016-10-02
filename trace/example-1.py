
import pg_logger
import json
import pprint

pp = pprint.PrettyPrinter(depth=2)

def finalizer(output_list):
  output_json = json.dumps(output_list)
  print(output_json)

file = open('test/test-1.py', 'r')
script_str = file.read()
print('====== Input code ======')
print(script_str)
print('')

print('===== Output trace =====')
results = pg_logger.exec_script_str(script_str, finalizer)



