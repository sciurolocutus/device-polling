import requests
from datetime import datetime
from pprint import pprint

#Disable SSL warnings
requests.packages.urllib3.disable_warnings()


def login(host = "192.168.0.1", username = 'admin', password = None):

  url = f"https://{host}/cgi/cgi_action"
  
  payload = f"username={username}&password=u2FkLAdm"
  headers = {
    'Connection': 'keep-alive',
    'Accept': '*/*',
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36'

  }
  
  response = requests.request("POST", url, headers=headers, data = payload, verify = False, allow_redirects = False)
  
  return response.cookies['Session-Id']


def get_connected_devices(host = "192.168.0.1", sessid = None):

  url = f"https://{host}/cgi/cgi_get?Object=Device.Hosts.Host&PhysAddress=&IPAddress=&HostName=&Active=&X_GWS_DeviceIcon=&Layer1Interface=&DHCPClient="
  
  payload = {}
  headers = {
    'Connection': 'keep-alive',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
  }
  
  jar = requests.cookies.RequestsCookieJar()
  jar.set('Session-Id', sessid)
  response = requests.request("GET", url, headers=headers, data = payload, verify = False, cookies = jar)
  
  response.raise_for_status()
  if response.status_code == 200:
    return response.json()

def parse_devices_response(resp):
  by_mac_address = {}
  objs = resp['Objects']
  for obj in objs:
    for param in obj['Param']:
        if param['ParamName'] == 'PhysAddress':
            mac = param['ParamValue']
        if param['ParamName'] == 'HostName':
            name = param['ParamValue']
        if param['ParamName'] == 'IPAddress':
            ip = param['ParamValue']
        if param['ParamName'] == 'Active':
            active = param['ParamValue'] == '1'
    by_mac_address[mac] = {'mac': mac, 'hostname': name, 'ip': ip, 'active': active}
    pprint(obj)
  return by_mac_address

if __name__ == '__main__':
  import configparser

  config = configparser.ConfigParser(delimiters=['='])
  config.read_file(open('config'))

  host = config['router']['hostname']
  username = config['router']['username']
  password = config['router']['password']
  sessionId = config.get('router', 'sessionId', fallback = None)

  if not(sessionId):
    print('Requesting a session id, as we do not have one stored.')
    sessionId = login(host, username, password)
    config['router']['sessionId'] = sessionId

  try:
    devices_response = get_connected_devices(host = host, sessid = sessionId)
  except requests.exceptions.HTTPError as err:
    print(err)
    print('Requesting a new session id, assuming that the error we just encountered was due to expired sessid')
    sessionId = login(host, username, password)
    config['router']['sessionId'] = sessionId
    devices_response = get_connected_devices(host = host, sessid = sessionId)

  devices = parse_devices_response(devices_response)
  request_ts = datetime.now()

  pprint(devices)

  # Initialize [in]active lists if not already.
  if not config.has_section('active'):
    config.add_section('active')
  if not config.has_section('inactive'):
    config.add_section('inactive')

  for mac in config['inactive']:
    if max in devices:
      if devices[mac]['active']:
        print(mac, ' just joined again!')

  
  print('Active list:')
  for obj in devices.values():
    if obj['active']:
      print(obj['mac'], ' ', obj['hostname'], ' ', obj['ip'])
      config['active'][obj['mac']] = request_ts.isoformat()
  
  print("\nInactive list:")
  for obj in devices.values():
    if not obj['active']:
      print(obj['mac'], ' ', obj['hostname'], ' ', obj['ip'])
      config['inactive'][obj['mac']] = request_ts.isoformat()
  
  with open('config', 'w+') as configFile:
    config.write(configFile)
