"""Controlled demo incidents; all effects remain inside SANAD's sandbox folder."""
SCENARIOS = {
 'service_outage': {'name':'Service outage','service':'orders-api','healthy':False,'config_ok':True,'requests_per_min':40,'failed_auth':0,'unauthorized_changes':False,'log':'Worker process exited unexpectedly; no suspicious authentication activity.'},
 'bad_configuration': {'name':'Invalid deployment configuration','service':'payments-api','healthy':False,'config_ok':False,'requests_per_min':45,'failed_auth':0,'unauthorized_changes':False,'log':'Deployment validation failed: invalid service configuration.'},
 'suspected_intrusion': {'name':'Suspected intrusion','service':'identity-api','healthy':False,'config_ok':False,'requests_per_min':950,'failed_auth':130,'unauthorized_changes':True,'log':'Unauthorized configuration modification and repeated authentication failures detected.'},
 'ambiguous_incident': {'name':'Ambiguous incident','service':'gateway-api','healthy':False,'config_ok':True,'requests_per_min':150,'failed_auth':12,'unauthorized_changes':False,'log':'Intermittent timeouts; root cause unclear.'},
 'multi_failure': {'name':'Cascading worker and queue failure','service':'fulfillment-api','healthy':True,'config_ok':True,'worker_running':False,'queue_depth':450,'requests_per_min':60,'failed_auth':0,'unauthorized_changes':False,'log':'Queue backlog increasing; background worker heartbeat missing.'}
}
