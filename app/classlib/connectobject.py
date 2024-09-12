import sys, os, requests, json;

class ConnectObject:
    def __init__(self):
        self.ip = "127.0.0.1";
        self.port = 80;
    
    def __execute__(self, class_name, method_name, parameters):
        envelop = { "class" : class_name, "method" :  method_name, "token" : "", "parameters" : parameters}
        url = "http://"+ self.ip +":80/cml/services/execute.php";
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'};
        r = requests.post(url, data=json.dumps(envelop), headers=headers);
        print(r.text);
        return json.loads(r.text);